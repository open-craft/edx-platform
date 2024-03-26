"""
Defines asynchronous celery task for content indexing
"""

from __future__ import annotations

import logging

from celery import shared_task
from celery_utils.logged_task import LoggedTask
from edx_django_utils.monitoring import set_code_owner_attribute
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import LibraryUsageLocatorV2

from . import api

log = logging.getLogger(__name__)


@shared_task(base=LoggedTask)
@set_code_owner_attribute
def upsert_xblock_index_doc(usage_key_str: str, recursive: bool, update_metadata: bool, update_tags: bool) -> bool:
    """
    Celery task to update the content index document for an XBlock
    """
    try:
        usage_key = UsageKey.from_string(usage_key_str)

        log.info("Updating content index document for XBlock with id: %s", usage_key)

        api.upsert_xblock_index_doc(usage_key, recursive, update_metadata, update_tags)

        return True
    except Exception as e:  # pylint: disable=broad-except pragma: no cover
        log.error("Error updating content index document for XBlock with id: %s. %s", usage_key_str, e)
        return False


@shared_task(base=LoggedTask)
@set_code_owner_attribute
def delete_xblock_index_doc(usage_key_str: str) -> bool:
    """
    Celery task to delete the content index document for an XBlock
    """
    try:
        usage_key = UsageKey.from_string(usage_key_str)

        log.info("Updating content index document for XBlock with id: %s", usage_key)

        api.delete_index_doc(usage_key)

        return True
    except Exception as e:  # pylint: disable=broad-except pragma: no cover
        log.error("Error deleting content index document for XBlock with id: %s. %s", usage_key_str, e)
        return False


@shared_task(base=LoggedTask)
@set_code_owner_attribute
def upsert_library_block_index_doc(usage_key_str: str, update_metadata: bool, update_tags: bool) -> bool:
    """
    Celery task to update the content index document for a library block
    """
    try:
        usage_key = LibraryUsageLocatorV2.from_string(usage_key_str)

        log.info("Updating content index document for library block with id: %s", usage_key)

        api.upsert_library_block_index_doc(usage_key, update_metadata, update_tags)

        return True
    except Exception as e:  # pylint: disable=broad-except pragma: no cover
        log.error("Error updating content index document for libray block with id: %s. %s", usage_key_str, e)
        return False


@shared_task(base=LoggedTask)
@set_code_owner_attribute
def delete_library_block_index_doc(usage_key_str: str) -> bool:
    """
    Celery task to delete the content index document for a library block
    """
    try:
        usage_key = LibraryUsageLocatorV2.from_string(usage_key_str)

        log.info("Deleting content index document for library block with id: %s", usage_key)

        api.delete_index_doc(usage_key)

        return True
    except Exception as e:  # pylint: disable=broad-except pragma: no cover
        log.error("Error deleting content index document for library block with id: %s. %s", usage_key_str, e)
        return False
