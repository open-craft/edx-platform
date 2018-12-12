"""
Models for reading and writing XBlock user state fields.

The largest size for any column in an InnoDB
index is 767 bytes. However, if we use MySQL's "utf8mb4", a.k.a. "actually
UTF-8", that limit goes down to 191 bytes (191 * 4 = 764). 

IDs for all models use bigint (64-bit) primary keys to support large datasets,
whether or not it's likely to be needed.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from django.conf import settings
from django.db import models
from jsonfield import JSONField
from model_utils.models import TimeStampedModel
from opaque_keys.edx.block_types import BlockTypeKeyV1, XBLOCK_V1
from opaque_keys.edx.django.models import (
    BlockTypeKeyField,
    CourseKeyField,
    UsageKeyField,
)
# Do not import any dependencies from edx-platform!
# This is meant to be an extractable app that doesn't depend
# on any LMS/CMS code.


class XBlockUserState(TimeStampedModel):
    """
    The successor to StudentModule, used to store user state data
    for XBlocks using the new XBlock runtime.

    This model does not need to support SQLite3 so does not use the
    "chunking manager" used by StudentModule
    """
    id = models.BigAutoField(primary_key=True)
    # block_type gets set automatically in save(), so don't set it manually
    block_type = BlockTypeKeyField(null=False, blank=False, db_index=True)
    usage_key = UsageKeyField(null=False, blank=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, on_delete=models.CASCADE)

    # The XBlock Scope.user_state field data for this XBlock, serialized as JSON.
    # Note: if no row exists in this table, that means that either the user
    # hasn't ever looked at the xblock, or the XBlock has never saved any Scope.user_state
    # field data.
    # If a row exists but has the value ``"{}"``, it means that the XBlock has at
    # some point stored state for that current user, but that that state has been deleted.
    state = JSONField(null=False, blank=False, default=dict)

    # There is no context_key or course_key field or separate index. To lookup by course, use
    # XBlockUserState.objects.filter(usage_key__context=course_key) which is just as efficient
    # as if there was a 'context_key' column, because it uses an efficient 'LIKE x%' query on
    # the usage_key index.

    class Meta(object):
        app_label = "xblock_state"
        unique_together = (
            ('student', 'usage_key'),
        )

    def save(self, *args, **kwargs):
        """
        We manage the block_type field automatically and don't want/allow users
        of this class to set it.
        """
        self.block_type = BlockTypeKeyV1(block_family=XBLOCK_V1, block_type=self.usage_key.block_type)
        super(XBlockUserState, self).save(*args, **kwargs)


class XBlockFieldBase(TimeStampedModel):
    """
    Base class for all XBlock field storage other than Scope.user_state fields,
    which are stored in XBlockUserState.
    """
    class Meta(object):
        app_label = "xblock_state"
        abstract = True

    # The name of the field
    field_name = models.CharField(max_length=64, db_index=True)

    # The value of the field. Defaults to None dumped as json
    value = JSONField(default=None)

    def __unicode__(self):
        keys = [field.name for field in self._meta.get_fields() if field.name not in ('created', 'modified')]
        return u'{}<{!r}'.format(self.__class__.__name__, {key: getattr(self, key) for key in keys})


class XModuleUserStateSummaryField(XBlockFieldBase):
    """
    Stores data set in the Scope.user_state_summary scope by an xmodule field
    """
    usage_id = UsageKeyField(max_length=255, db_index=True)

    class Meta(object):
        unique_together = (('usage_id', 'field_name'),)


class XModuleStudentPrefsField(XBlockFieldBase):
    """
    Stores data set in the Scope.preferences scope by an xmodule field
    """
    module_type = BlockTypeKeyField(max_length=64, db_index=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, on_delete=models.CASCADE)

    class Meta(object):
        unique_together = (('student', 'module_type', 'field_name'),)


class XModuleStudentInfoField(XBlockFieldBase):
    """
    Stores data set in the Scope.preferences scope by an xmodule field
    """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, on_delete=models.CASCADE)

    class Meta(object):
        unique_together = (('student', 'field_name'),)
