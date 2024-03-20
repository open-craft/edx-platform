"""
Handlers for content indexing
"""

import logging

from django.conf import settings
from django.dispatch import receiver
from openedx_events.content_authoring.data import XBlockData
from openedx_events.content_authoring.signals import (
    XBLOCK_CREATED,
    XBLOCK_DELETED,
    XBLOCK_UPDATED
)

from .tasks import delete_xblock_index_doc, upsert_xblock_index_doc
from .api import is_meilisearch_enabled

log = logging.getLogger(__name__)


@receiver(XBLOCK_CREATED)
def xblock_created_handler(**kwargs) -> None:
    """
    Create the index for the XBlock
    """
    if not is_meilisearch_enabled():
        return

    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):
        log.error("Received null or incorrect data for event")
        return

    upsert_xblock_index_doc.delay(
        str(xblock_info.usage_key),
        recursive=False,
        update_metadata=True,
        update_tags=False,
    )


@receiver(XBLOCK_UPDATED)
def xblock_updated_handler(**kwargs) -> None:
    """
    Update the index for the XBlock and its children
    """
    if not is_meilisearch_enabled():
        return

    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):
        log.error("Received null or incorrect data for event")
        return

    upsert_xblock_index_doc.delay(
        str(xblock_info.usage_key),
        recursive=True,  # Update all children because the breadcrumb may have changed
        update_metadata=True,
        update_tags=False,
    )


@receiver(XBLOCK_DELETED)
def xblock_deleted_handler(**kwargs) -> None:
    """
    Delete the index for the XBlock
    """
    if not is_meilisearch_enabled():
        return

    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):
        log.error("Received null or incorrect data for event")
        return

    delete_xblock_index_doc.delay(str(xblock_info.usage_key))
