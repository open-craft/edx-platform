"""
Handlers for content indexing
"""

import logging

from django.dispatch import receiver
from openedx_events.content_authoring.data import LibraryBlockData, XBlockData
from openedx_events.content_authoring.signals import (
    LIBRARY_BLOCK_CREATED,
    LIBRARY_BLOCK_DELETED,
    LIBRARY_BLOCK_UPDATED,
    XBLOCK_CREATED,
    XBLOCK_DELETED,
    XBLOCK_UPDATED
)

from .api import only_if_meilisearch_enabled
from .tasks import (
    delete_library_block_index_doc,
    delete_xblock_index_doc,
    upsert_library_block_index_doc,
    upsert_xblock_index_doc
)

log = logging.getLogger(__name__)


@receiver(XBLOCK_CREATED)
@only_if_meilisearch_enabled
def xblock_created_handler(**kwargs) -> None:
    """
    Create the index for the XBlock
    """
    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):  # pragma: no cover
        log.error("Received null or incorrect data for event")
        return

    upsert_xblock_index_doc.delay(
        str(xblock_info.usage_key),
        recursive=False,
        update_metadata=True,
        update_tags=False,
    )


@receiver(XBLOCK_UPDATED)
@only_if_meilisearch_enabled
def xblock_updated_handler(**kwargs) -> None:
    """
    Update the index for the XBlock and its children
    """
    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):  # pragma: no cover
        log.error("Received null or incorrect data for event")
        return

    upsert_xblock_index_doc.delay(
        str(xblock_info.usage_key),
        recursive=True,  # Update all children because the breadcrumb may have changed
        update_metadata=True,
        update_tags=False,
    )


@receiver(XBLOCK_DELETED)
@only_if_meilisearch_enabled
def xblock_deleted_handler(**kwargs) -> None:
    """
    Delete the index for the XBlock
    """
    xblock_info = kwargs.get("xblock_info", None)
    if not xblock_info or not isinstance(xblock_info, XBlockData):  # pragma: no cover
        log.error("Received null or incorrect data for event")
        return

    delete_xblock_index_doc.delay(str(xblock_info.usage_key))


@receiver(LIBRARY_BLOCK_CREATED)
@only_if_meilisearch_enabled
def content_library_updated_handler(**kwargs) -> None:
    """
    Create or update the index for the content library block
    """
    library_block_data = kwargs.get("library_block", None)
    if not library_block_data or not isinstance(library_block_data, LibraryBlockData):  # pragma: no cover
        log.error("Received null or incorrect data for event")
        return

    upsert_library_block_index_doc.delay(str(library_block_data.usage_key), update_metadata=True, update_tags=False)


@receiver(LIBRARY_BLOCK_DELETED)
@only_if_meilisearch_enabled
def content_library_deleted_handler(**kwargs) -> None:
    """
    Delete the index for the content library block
    """
    library_block_data = kwargs.get("library_block", None)
    if not library_block_data or not isinstance(library_block_data, LibraryBlockData):  # pragma: no cover
        log.error("Received null or incorrect data for event")
        return

    delete_library_block_index_doc.delay(str(library_block_data.usage_key))
