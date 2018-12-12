"""
An implementation of :class:`XBlockUserStateClient`, which stores XBlock Scope.user_state
field data in the XBlockUserState Django ORM model.

This is distinct from DjangoXBlockUserStateClient which stores state and scores together
in the (older) StudentModule model.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import json
import logging
from operator import attrgetter
import six
from time import time

from django.conf import settings
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db import transaction
from django.db.utils import IntegrityError
import dogstats_wrapper as dog_stats_api
from edx_django_utils import monitoring as monitoring_utils
from edx_user_state_client.interface import XBlockUserState, XBlockUserStateClient
from opaque_keys.edx.block_types import BlockTypeKeyV1, XBLOCK_V1
from xblock.fields import Scope

# Do not import any dependencies from edx-platform outside of this module!
# This is meant to be an extractable app that doesn't depend
# on any LMS/CMS code.

from .models import XBlockUserState


log = logging.getLogger(__name__)


class DjangoXBlockUserStateClient2(XBlockUserStateClient):
    """
    An interface that uses the Django ORM XBlockUserState as a backend.

    See also InstrumentedDjangoXBlockUserStateClient2 which is the same but which
    outputs useful metrics for monitoring and performance optimization.
    """

    def get_many(self, username, block_keys, scope=Scope.user_state, fields=None):
        """
        Retrieve the stored XBlock state for the specified XBlock usages.

        Arguments:
            username: The name of the user whose state should be retrieved
            block_keys ([UsageKey]): A list of UsageKeys identifying which xblock states to load.
            scope (Scope): The scope to load data from
            fields: A list of field values to retrieve. If None, retrieve all stored fields.

        Yields:
            XBlockUserState tuples for each specified UsageKey in block_keys.
            field_state is a dict mapping field names to values.
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported, not {}".format(scope))

        block_data_rows = XBlockUserState.objects.filter(
            usage_key__in=block_keys,
            student__username=username,
        )
        for module, usage_key in block_data_rows:
            # If the state is the empty dict, then it has been deleted, and so
            # conformant UserStateClients should treat it as if it doesn't exist.
            if state == {}:
                continue

            # filter state on fields
            if fields is not None:
                state = {
                    field: state[field]
                    for field in fields
                    if field in state
                }
            yield XBlockUserState(username, usage_key, state, module.modified, scope)

    def set_many(self, username, block_keys_to_state, scope=Scope.user_state):
        """
        Set fields for a particular XBlock.

        Arguments:
            username: The name of the user whose state should be retrieved
            block_keys_to_state (dict): A dict mapping UsageKeys to state dicts.
                Each state dict maps field names to values. These state dicts
                are overlaid over the stored state. To delete fields, use
                :meth:`delete` or :meth:`delete_many`.
            scope (Scope): The scope to load data from
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported")

        user = User.objects.get(username=username)

        if user.is_anonymous:
            # Anonymous users cannot be persisted to the database, so let's just use
            # what we have.
            return

        for usage_key, state in block_keys_to_state.items():
            self._set_one(user, usage_key, state)

    def _set_one(self, user, usage_key, state):
        """
        Internal method to save the state of a single XBlock for a single user.

        Returns some basic stats: (num_fields_before, num_fields_after, created)
        """
        try:
            state_obj, created = XBlockUserState.objects.get_or_create(
                student=user,
                usage_key=usage_key,
                defaults={'state': state},
            )
        except IntegrityError:
            # PLAT-1109 - Until we switch to read committed, we cannot rely
            # on get_or_create to be able to see rows created in another
            # process. This seems to happen frequently, and ignoring it is the
            # best course of action for now
            log.warning("set_many: IntegrityError for student %s - usage key %s", user.username, usage_key)
            return (None, None, None)

        num_fields_before = num_fields_after = len(state)
        if not created:
            current_state = state_obj.state
            num_fields_before = len(current_state)
            current_state.update(state)
            num_fields_after = len(current_state)
            state_obj.state = current_state
            try:
                with transaction.atomic():
                    # Updating the object - force_update guarantees no INSERT will occur.
                    state_obj.save(force_update=True)
            except IntegrityError:
                # The UPDATE above failed. Log information - but ignore the error.
                # See https://openedx.atlassian.net/browse/TNL-5365
                log.warning("set_many: IntegrityError for student %s - usage key %s", user.username, usage_key)
        return (num_fields_before, num_fields_after, created)

    def delete_many(self, username, block_keys, scope=Scope.user_state, fields=None):
        """
        Delete the stored XBlock state for a many xblock usages.

        Arguments:
            username: The name of the user whose state should be deleted
            block_keys (list): The UsageKey identifying which xblock state to delete.
            scope (Scope): The scope to delete data from
            fields: A list of fields to delete. If None, delete all stored fields.
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported")

        block_data_rows = XBlockUserState.objects.filter(
            usage_key__in=block_keys,
            student__username=username,
        )
        for state_obj in block_data_rows:
            if fields is None:
                state_obj.state = {}
            else:
                for field in fields:
                    if field in state_obj.state:
                        del state_obj.state[field]

            # We just read this object, so we know that we can do an update
            state_obj.save(force_update=True)

    def get_history(self, username, block_key, scope=Scope.user_state):
        raise NotImplementedError

    def iter_all_for_block(self, block_key, scope=Scope.user_state):
        """
        Return an iterator over the data stored in the block (e.g. a problem block).

        You get no ordering guarantees. If you're using this method, you should be running in an
        async task.

        Arguments:
            block_key: an XBlock's locator (e.g. :class:`~BlockUsageLocator`)
            scope (Scope): must be `Scope.user_state`

        Returns:
            an iterator over all data. Each invocation returns the next :class:`~XBlockUserState`
                object, which includes the block's contents.
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported")

        results = XBlockUserState.objects.order_by('id').filter(usage_key=block_key)
        return self._iterate_state_objects(results)

    def _iterate_state_objects(self, results):
        """
        Internal helper method to yield paged iteration over XBlockUserState objects.
        """
        p = Paginator(results, settings.USER_STATE_BATCH_SIZE)
        for page_number in p.page_range:
            page = p.page(page_number)
            for obj in page.object_list:
                if obj.state == {}:
                    continue
                yield XBlockUserState(obj.student.username, obj.module_state_key, obj.state, obj.modified, scope)

    def iter_all_for_course(self, course_key, block_type=None, scope=Scope.user_state):
        """
        Return an iterator over all data stored in a course's blocks.

        You get no ordering guarantees. If you're using this method, you should be running in an
        async task.

        Arguments:
            course_key: a course locator
            scope (Scope): must be `Scope.user_state`

        Returns:
            an iterator over all data. Each invocation returns the next :class:`~XBlockUserState`
                object, which includes the block's contents.
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported")

        results = XBlockUserState.objects.order_by('id').filter(usage_key__course=course_key)
        if block_type:
            block_type_key = BlockTypeKeyV1(block_family=XBLOCK_V1, block_type=block_type)
            results = results.filter(block_type=block_type_key)
        return self._iterate_state_objects(results)


class InstrumentedDjangoXBlockUserStateClient2(XBlockUserStateClient):
    """
    A version of DjangoXBlockUserStateClient2 (An XBlock Scope.user_state field
    value client that uses the Django ORM XBlockUserState model as a backend.)
    that is instrumented for recording metrics to DataDog and New Relic.
    """
    # Use this sample rate for DataDog events.
    API_DATADOG_SAMPLE_RATE = 0.1

    def _ddog_increment(self, evt_time, evt_name):
        """
        DataDog increment method.
        """
        dog_stats_api.increment(
            'DjangoXBlockUserStateClient2.{}'.format(evt_name),
            timestamp=evt_time,
            sample_rate=self.API_DATADOG_SAMPLE_RATE,
        )

    def _ddog_histogram(self, evt_time, evt_name, value):
        """
        DataDog histogram method.
        """
        dog_stats_api.histogram(
            'DjangoXBlockUserStateClient2.{}'.format(evt_name),
            value,
            timestamp=evt_time,
            sample_rate=self.API_DATADOG_SAMPLE_RATE,
        )

    def _nr_metric_name(self, function_name, stat_name, block_type=None):
        """
        Return a metric name (string) representing the provided descriptors.
        The return value is directly usable for custom NR metrics.
        """
        if block_type is None:
            metric_name_parts = ['xb_user_state', function_name, stat_name]
        else:
            metric_name_parts = ['xb_user_state', function_name, block_type, stat_name]
        return '.'.join(metric_name_parts)

    def _nr_stat_accumulate(self, function_name, stat_name, value):
        """
        Accumulate arbitrary NR stats (not specific to block types).
        """
        monitoring_utils.accumulate(
            self._nr_metric_name(function_name, stat_name),
            value
        )

    def _nr_stat_increment(self, function_name, stat_name, count=1):
        """
        Increment arbitrary NR stats (not specific to block types).
        """
        self._nr_stat_accumulate(function_name, stat_name, count)

    def _nr_block_stat_accumulate(self, function_name, block_type, stat_name, value):
        """
        Accumulate NR stats related to block types.
        """
        monitoring_utils.accumulate(
            self._nr_metric_name(function_name, stat_name),
            value,
        )
        monitoring_utils.accumulate(
            self._nr_metric_name(function_name, stat_name, block_type=block_type),
            value,
        )

    def _nr_block_stat_increment(self, function_name, block_type, stat_name, count=1):
        """
        Increment NR stats related to block types.
        """
        self._nr_block_stat_accumulate(function_name, block_type, stat_name, count)

    @property
    def base_impl(self):
        """ Shortcut to work around Python2.7's verbose super() syntax """
        return super(InstrumentedDjangoXBlockUserStateClient2, self)

    def get_many(self, username, block_keys, scope=Scope.user_state, fields=None):
        """
        Retrieve the stored XBlock state for the specified XBlock usages.

        Arguments:
            username: The name of the user whose state should be retrieved
            block_keys ([UsageKey]): A list of UsageKeys identifying which xblock states to load.
            scope (Scope): The scope to load data from
            fields: A list of field values to retrieve. If None, retrieve all stored fields.

        Yields:
            XBlockUserState tuples for each specified UsageKey in block_keys.
            field_state is a dict mapping field names to values.
        """
        total_block_count = 0
        evt_time = time()

        # count how many times this function gets called
        self._nr_stat_increment('get_many', 'calls')

        # keep track of blocks requested
        self._ddog_histogram(evt_time, 'get_many.blks_requested', len(block_keys))
        self._nr_stat_accumulate('get_many', 'blocks_requested', len(block_keys))

        for state in self.base_impl.get_many(username, block_keys, scope, fields):
            self._nr_block_stat_increment('get_many', usage_key.block_type, 'blocks_out')
            total_block_count += 1
            yield state

        finish_time = time()
        duration = (finish_time - evt_time) * 1000  # milliseconds

        self._ddog_histogram(evt_time, 'get_many.blks_out', total_block_count)
        self._ddog_histogram(evt_time, 'get_many.response_time', duration)
        self._nr_stat_accumulate('get_many', 'duration', duration)

    def set_many(self, username, block_keys_to_state, scope=Scope.user_state):
        """
        Set fields for a particular XBlock.

        Arguments:
            username: The name of the user whose state should be retrieved
            block_keys_to_state (dict): A dict mapping UsageKeys to state dicts.
                Each state dict maps field names to values. These state dicts
                are overlaid over the stored state. To delete fields, use
                :meth:`delete` or :meth:`delete_many`.
            scope (Scope): The scope to load data from
        """
        # count how many times this function gets called
        self._nr_stat_increment('set_many', 'calls')

        evt_time = time()

        self.base_impl.set_many(username, block_keys_to_state, scope)

        # Events for the entire set_many call.
        finish_time = time()
        duration = (finish_time - evt_time) * 1000  # milliseconds
        self._ddog_histogram(evt_time, 'set_many.blks_updated', len(block_keys_to_state))
        self._ddog_histogram(evt_time, 'set_many.response_time', duration)
        self._nr_stat_accumulate('set_many', 'duration', duration)

    def _set_one(self, user, usage_key, state):
        """
        Internal method to save the state of a single XBlock for a single user.

        Returns some basic stats: (num_fields_before, num_fields_after)
        """
        num_fields_before, num_fields_after, created = self.base_impl._set_one(username, usage_key, state)
        if num_fields_before is None:
            # Base implementation short-circuited due to DB read consistency issue.
            self._ddog_increment(evt_time, 'set_many.integrity_error')
        num_fields_updated = 0
        # Record whether a state row has been created or updated.
        if created:
            self._ddog_increment(evt_time, 'set_many.state_created')
            self._nr_block_stat_increment('set_many', usage_key.block_type, 'blocks_created')
        else:
            self._ddog_increment(evt_time, 'set_many.state_updated')
            self._nr_block_stat_increment('set_many', usage_key.block_type, 'blocks_updated')

        # Event to record number of fields sent in to set/set_many.
        self._ddog_histogram(evt_time, 'set_many.fields_in', len(state))

        # Event to record number of new fields set in set/set_many.
        num_new_fields_set = num_fields_after - num_fields_before
        self._ddog_histogram(evt_time, 'set_many.fields_set', num_new_fields_set)

        # Event to record number of existing fields updated in set/set_many.
        num_fields_updated = max(0, len(state) - num_new_fields_set)
        self._ddog_histogram(evt_time, 'set_many.fields_updated', num_fields_updated)

    def delete_many(self, username, block_keys, scope=Scope.user_state, fields=None):
        """
        Delete the stored XBlock state for a many xblock usages.

        Arguments:
            username: The name of the user whose state should be deleted
            block_keys (list): The UsageKey identifying which xblock state to delete.
            scope (Scope): The scope to delete data from
            fields: A list of fields to delete. If None, delete all stored fields.
        """
        if scope != Scope.user_state:
            raise ValueError("Only Scope.user_state is supported")

        evt_time = time()
        if fields is None:
            self._ddog_increment(evt_time, 'delete_many.empty_state')
        else:
            self._ddog_histogram(evt_time, 'delete_many.field_count', len(fields))

        self._ddog_histogram(evt_time, 'delete_many.block_count', len(block_keys))

        self.base_impl.delete_many(username, block_keys, scope, fields)

        # Event for the entire delete_many call.
        finish_time = time()
        self._ddog_histogram(evt_time, 'delete_many.response_time', (finish_time - evt_time) * 1000)
