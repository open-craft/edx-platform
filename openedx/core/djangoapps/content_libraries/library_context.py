"""
Definition of "Library" as a learning context.
"""
import logging

from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import NotFound

from openedx_events.content_authoring.data import LibraryBlockData
from openedx_events.content_authoring.signals import LIBRARY_BLOCK_UPDATED
from opaque_keys.edx.keys import UsageKeyV2
from openedx_learning.api import authoring as authoring_api

from openedx.core.djangoapps.content_libraries import api, permissions
from openedx.core.djangoapps.content_libraries.models import ContentLibrary
from openedx.core.djangoapps.xblock.api import LearningContext
from openedx.core.types import User as UserType

log = logging.getLogger(__name__)


class LibraryContextImpl(LearningContext):
    """
    Implements content libraries as a learning context.

    This is the *new* content libraries based on Learning Core, not the old content
    libraries based on modulestore.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.use_draft = kwargs.get('use_draft', None)

    def can_edit_block(self, user: UserType, usage_key: UsageKeyV2) -> bool:
        """
        Assuming a block with the specified ID (usage_key) exists, does the
        specified user have permission to edit it (make changes to the
        fields / authored data store)?

        May raise ContentLibraryNotFound if the library does not exist.
        """
        try:
            api.require_permission_for_library_key(usage_key.lib_key, user, permissions.CAN_EDIT_THIS_CONTENT_LIBRARY)
            return True
        except PermissionDenied:
            return False
        except api.ContentLibraryNotFound:
            # A 404 is probably what you want in this case, not a 500 error, so do that by default.
            raise NotFound(f"Content Library '{usage_key.lib_key}' does not exist")

    def can_view_block_for_editing(self, user: UserType, usage_key: UsageKeyV2) -> bool:
        """
        Assuming a block with the specified ID (usage_key) exists, does the
        specified user have permission to view its fields and OLX details (but
        not necessarily to make changes to it)?

        May raise ContentLibraryNotFound if the library does not exist.
        """
        try:
            api.require_permission_for_library_key(usage_key.lib_key, user, permissions.CAN_VIEW_THIS_CONTENT_LIBRARY)
            return True
        except PermissionDenied:
            return False
        except api.ContentLibraryNotFound:
            # A 404 is probably what you want in this case, not a 500 error, so do that by default.
            raise NotFound(f"Content Library '{usage_key.lib_key}' does not exist")

    def can_view_block(self, user: UserType, usage_key: UsageKeyV2) -> bool:
        """
        Does the specified usage key exist in its context, and if so, does the
        specified user have permission to view it and interact with it (call
        handlers, save user state, etc.)?

        May raise ContentLibraryNotFound if the library does not exist.
        """
        try:
            api.require_permission_for_library_key(
                usage_key.lib_key, user, permissions.CAN_LEARN_FROM_THIS_CONTENT_LIBRARY,
            )
            return True
        except PermissionDenied:
            return False
        except api.ContentLibraryNotFound:
            # A 404 is probably what you want in this case, not a 500 error, so do that by default.
            raise NotFound(f"Content Library '{usage_key.lib_key}' does not exist")

    def block_exists(self, usage_key: UsageKeyV2):
        """
        Does the block for this usage_key exist in this Library?

        Note that this applies to all versions, i.e. you can put a usage key for
        a piece of content that has been soft-deleted (removed from Drafts), and
        it will still return True here. That's because for the purposes of
        permission checking, we just want to know whether that block has ever
        existed in this Library, because we could be looking at any older
        version of it.
        """
        try:
            content_lib = ContentLibrary.objects.get_by_key(usage_key.context_key)
        except ContentLibrary.DoesNotExist:
            return False

        learning_package = content_lib.learning_package
        if learning_package is None:
            return False

        return authoring_api.component_exists_by_key(
            learning_package.id,
            namespace='xblock.v1',
            type_name=usage_key.block_type,
            local_key=usage_key.block_id,
        )

    def send_block_updated_event(self, usage_key: UsageKeyV2):
        """
        Send a "block updated" event for the library block with the given usage_key.

        usage_key: the UsageKeyV2 subclass used for this learning context
        """
        LIBRARY_BLOCK_UPDATED.send_event(
            library_block=LibraryBlockData(
                library_key=usage_key.lib_key,
                usage_key=usage_key,
            )
        )
