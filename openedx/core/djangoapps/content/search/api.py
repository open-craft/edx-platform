"""
Content index and search API using Meilisearch
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable, Generator

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from meilisearch import Client as MeilisearchClient
from meilisearch.errors import MeilisearchError
from meilisearch.models.task import TaskInfo
from opaque_keys.edx.keys import UsageKey

from openedx.core.djangoapps.content.search.documents import (
    STUDIO_INDEX_NAME,
    Fields,
    meili_id_from_opaque_key,
    searchable_doc_for_course_block,
    searchable_doc_for_library_block
)
from openedx.core.djangoapps.content_libraries import api as lib_api
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

from .documents import Fields, searchable_doc_for_course_block, searchable_doc_for_library_block

log = logging.getLogger(__name__)

User = get_user_model()

STUDIO_INDEX_NAME = "studio_content"

if hasattr(settings, "MEILISEARCH_INDEX_PREFIX"):
    INDEX_NAME = settings.MEILISEARCH_INDEX_PREFIX + STUDIO_INDEX_NAME
else:
    INDEX_NAME = STUDIO_INDEX_NAME


_MEILI_CLIENT = None
_MEILI_API_KEY_UID = None

LOCK_EXPIRE = 5 * 60  # Lock expires in 5 minutes


@contextmanager
def _index_rebuild_lock() -> Generator[str, None, None]:
    """
    Lock to prevent that more than one rebuild is running at the same time
    """
    timeout_at = time.monotonic() + LOCK_EXPIRE
    lock_id = f"lock-meilisearch-index-{INDEX_NAME}"
    new_index_name = INDEX_NAME + "_new"

    while True:
        status = cache.add(lock_id, new_index_name, LOCK_EXPIRE)
        if status:
            # Lock acquired
            try:
                yield new_index_name
                break
            finally:
                # Release the lock
                cache.delete(lock_id)

        if time.monotonic() > timeout_at:
            raise TimeoutError("Timeout acquiring lock")

        time.sleep(1)


def _get_running_rebuild_index_name() -> str | None:
    lock_id = f"lock-meilisearch-index-{INDEX_NAME}"

    return cache.get(lock_id)


def _get_meilisearch_client():
    """
    Get the Meiliesearch client
    """
    global _MEILI_CLIENT  # pylint: disable=global-statement

    # Connect to Meilisearch
    if not is_meilisearch_enabled():
        raise RuntimeError("MEILISEARCH_ENABLED is not set - search functionality disabled.")

    if _MEILI_CLIENT is not None:
        return _MEILI_CLIENT

    _MEILI_CLIENT = MeilisearchClient(settings.MEILISEARCH_URL, settings.MEILISEARCH_API_KEY)
    try:
        _MEILI_CLIENT.health()
    except MeilisearchError as err:
        _MEILI_CLIENT = None
        raise ConnectionError("Unable to connect to Meilisearch") from err
    return _MEILI_CLIENT


def clear_meilisearch_client():
    global _MEILI_CLIENT  # pylint: disable=global-statement

    _MEILI_CLIENT = None


def _get_meili_api_key_uid():
    """
    Helper method to get the UID of the API key we're using for Meilisearch
    """
    global _MEILI_API_KEY_UID  # pylint: disable=global-statement

    if _MEILI_API_KEY_UID is not None:
        return _MEILI_API_KEY_UID

    _MEILI_API_KEY_UID = _get_meilisearch_client().get_key(settings.MEILISEARCH_API_KEY).uid


def _wait_for_meili_task(info: TaskInfo) -> None:
    """
    Simple helper method to wait for a Meilisearch task to complete
    """
    client = _get_meilisearch_client()
    current_status = client.get_task(info.task_uid)
    while current_status.status in ("enqueued", "processing"):
        time.sleep(1)
        current_status = client.get_task(info.task_uid)
    if current_status.status != "succeeded":
        try:
            err_reason = current_status.error['message']
        except (TypeError, KeyError):
            err_reason = "Unknown error"
        raise MeilisearchError(err_reason)


def _wait_for_meili_tasks(info_list: list[TaskInfo]) -> None:
    """
    Simple helper method to wait for multiple Meilisearch tasks to complete
    """
    while info_list:
        info = info_list.pop()
        _wait_for_meili_task(info)


def _index_exists(index_name: str) -> bool:
    """
    Check if an index exists
    """
    client = _get_meilisearch_client()
    try:
        client.get_index(index_name)
    except MeilisearchError as err:
        if err.code == "index_not_found":
            return False
        else:
            raise err
    return True


@contextmanager
def _using_temp_index(status_cb: Callable[[str], None] | None = None) -> Generator[str, None, None]:
    """
    Create a new temporary Meilisearch index, populate it, then swap it to
    become the active index.
    """
    def nop(_):  # pragma: no cover
        pass

    if status_cb is None:
        status_cb = nop

    client = _get_meilisearch_client()
    status_cb("Checking index...")
    with _index_rebuild_lock() as temp_index_name:
        if _index_exists(temp_index_name):
            status_cb("Temporary index already exists. Deleting it...")
            _wait_for_meili_task(client.delete_index(temp_index_name))

        status_cb("Creating new index...")
        _wait_for_meili_task(
            client.create_index(temp_index_name, {'primaryKey': 'id'})
        )
        new_index_created = client.get_index(temp_index_name).created_at

        yield temp_index_name

        if not _index_exists(INDEX_NAME):
            # We have to create the "target" index before we can successfully swap the new one into it:
            status_cb("Preparing to swap into index (first time)...")
            _wait_for_meili_task(client.create_index(INDEX_NAME))
        status_cb("Swapping index...")
        client.swap_indexes([{'indexes': [temp_index_name, INDEX_NAME]}])
        # If we're using an API key that's restricted to certain index prefix(es), we won't be able to get the status
        # of this request unfortunately. https://github.com/meilisearch/meilisearch/issues/4103
        while True:
            time.sleep(1)
            if client.get_index(INDEX_NAME).created_at != new_index_created:
                status_cb("Waiting for swap completion...")
            else:
                break
        status_cb("Deleting old index...")
        _wait_for_meili_task(client.delete_index(temp_index_name))


def _recurse_children(block, fn, status_cb: Callable[[str], None] | None = None) -> None:
    """
    Recurse the children of an XBlock and call the given function for each

    The main purpose of this is just to wrap the loading of each child in
    try...except. Otherwise block.get_children() would do what we need.
    """
    if block.has_children:
        for child_id in block.children:
            try:
                child = block.get_child(child_id)
            except Exception as err:  # pylint: disable=broad-except
                log.exception(err)
                if status_cb is not None:
                    status_cb(f"Unable to load block {child_id}")
            else:
                fn(child)


def only_if_meilisearch_enabled(f):
    """
    Only call `f` if meilisearch is enabled
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        """Wraps the decorated function."""
        if is_meilisearch_enabled():
            return f(*args, **kwargs)
    return wrapper


def is_meilisearch_enabled() -> bool:
    """
    Returns whether Meilisearch is enabled
    """
    if hasattr(settings, "MEILISEARCH_INDEX_PREFIX"):
        return settings.MEILISEARCH_ENABLED

    return False


def rebuild_index(status_cb: Callable[[str], None] | None = None) -> None:
    """
    Rebuild the Meilisearch index from scratch
    """
    def nop(_message):
        pass

    if status_cb is None:
        status_cb = nop

    client = _get_meilisearch_client()
    store = modulestore()

    # Get the lists of libraries
    status_cb("Counting libraries...")
    lib_keys = [lib.library_key for lib in lib_api.ContentLibrary.objects.select_related('org').only('org', 'slug')]
    num_libraries = len(lib_keys)

    # Get the list of courses
    status_cb("Counting courses...")
    with store.branch_setting(ModuleStoreEnum.Branch.draft_preferred):
        all_courses = store.get_courses()
    num_courses = len(all_courses)

    # Some counters so we can track our progress as indexing progresses:
    num_contexts = num_courses + num_libraries
    num_contexts_done = 0  # How many courses/libraries we've indexed
    num_blocks_done = 0  # How many individual components/XBlocks we've indexed

    status_cb(f"Found {num_courses} courses and {num_libraries} libraries.")
    with _using_temp_index(status_cb) as temp_index_name:
        ############## Configure the index ##############

        # The following index settings are best changed on an empty index.
        # Changing them on a populated index will "re-index all documents in the index, which can take some time"
        # and use more RAM. Instead, we configure an empty index then populate it one course/library at a time.

        # Mark usage_key as unique (it's not the primary key for the index, but nevertheless must be unique):
        client.index(temp_index_name).update_distinct_attribute(Fields.usage_key)
        # Mark which attributes can be used for filtering/faceted search:
        client.index(temp_index_name).update_filterable_attributes([
            Fields.block_type,
            Fields.context_key,
            Fields.org,
            Fields.tags,
            Fields.type,
        ])

        ############## Libraries ##############
        status_cb("Indexing libraries...")
        for lib_key in lib_keys:
            status_cb(f"{num_contexts_done + 1}/{num_contexts}. Now indexing library {lib_key}")
            docs = []
            for component in lib_api.get_library_components(lib_key):
                metadata = lib_api.LibraryXBlockMetadata.from_component(lib_key, component)
                doc = searchable_doc_for_library_block(metadata)
                docs.append(doc)
                num_blocks_done += 1
            if docs:
                # Add all the docs in this library at once (usually faster than adding one at a time):
                _wait_for_meili_task(client.index(temp_index_name).add_documents(docs))
            num_contexts_done += 1

        ############## Courses ##############
        status_cb("Indexing courses...")
        for course in all_courses:
            status_cb(
                f"{num_contexts_done + 1}/{num_contexts}. Now indexing course {course.display_name} ({course.id})"
            )
            docs = []

            # Pre-fetch the course with all of its children:
            course = store.get_course(course.id, depth=None)

            def add_with_children(block):
                """ Recursively index the given XBlock/component """
                doc = searchable_doc_for_course_block(block)
                docs.append(doc)  # pylint: disable=cell-var-from-loop
                _recurse_children(block, add_with_children)  # pylint: disable=cell-var-from-loop

            _recurse_children(course, add_with_children)

            if docs:
                # Add all the docs in this course at once (usually faster than adding one at a time):
                _wait_for_meili_task(client.index(temp_index_name).add_documents(docs))
            num_contexts_done += 1
            num_blocks_done += len(docs)

    status_cb(f"Done! {num_blocks_done} blocks indexed across {num_contexts_done} courses and libraries.")


def upsert_xblock_index_doc(
    usage_key: UsageKey, recursive: bool = True, update_metadata: bool = True, update_tags: bool = True
) -> None:
    """
    Creates or updates the document for the given XBlock in the search index


    Args:
        usage_key (UsageKey): The usage key of the XBlock to index
        recursive (bool): If True, also index all children of the XBlock
        update_metadata (bool): If True, update the metadata of the XBlock
        update_tags (bool): If True, update the tags of the XBlock
    """
    current_rebuild_index_name = _get_running_rebuild_index_name()

    xblock = modulestore().get_item(usage_key)
    client = _get_meilisearch_client()

    docs = []

    def add_with_children(block):
        """ Recursively index the given XBlock/component """
        doc = searchable_doc_for_course_block(block, include_metadata=update_metadata, include_tags=update_tags)
        docs.append(doc)
        if recursive:
            _recurse_children(block, add_with_children)

    add_with_children(xblock)

    tasks = []
    if current_rebuild_index_name:
        # If there is a rebuild in progress, the document will also be added to the new index.
        tasks.append(client.index(current_rebuild_index_name).update_documents(docs))
    tasks.append(client.index(INDEX_NAME).update_documents(docs))

    _wait_for_meili_tasks(tasks)


def delete_index_doc(usage_key: UsageKey) -> None:
    """
    Deletes the document for the given XBlock from the search index

    Args:
        usage_key (UsageKey): The usage key of the XBlock to be removed from the index
    """
    current_rebuild_index_name = _get_running_rebuild_index_name()

    client = _get_meilisearch_client()

    tasks = []
    if current_rebuild_index_name:
        # If there is a rebuild in progress, the document will also be added to the new index.
        tasks.append(client.index(current_rebuild_index_name).delete_document(meili_id_from_opaque_key(usage_key)))
    tasks.append(client.index(INDEX_NAME).delete_document(meili_id_from_opaque_key(usage_key)))

    _wait_for_meili_tasks(tasks)


def upsert_library_block_index_doc(
    usage_key: UsageKey, update_metadata: bool = True, update_tags: bool = True
) -> None:
    """
    Creates or updates the document for the given Library Block in the search index


    Args:
        usage_key (UsageKey): The usage key of the Library Block to index
        update_metadata (bool): If True, update the metadata of the Library Block
        update_tags (bool): If True, update the tags of the Library Block
    """
    current_rebuild_index_name = _get_running_rebuild_index_name()

    library_block = lib_api.get_component_from_usage_key(usage_key)
    library_block_metadata = lib_api.LibraryXBlockMetadata.from_component(usage_key.context_key, library_block)
    client = _get_meilisearch_client()

    docs = [
        searchable_doc_for_library_block(
            library_block_metadata, include_metadata=update_metadata, include_tags=update_tags
        )
    ]

    tasks = []
    if current_rebuild_index_name:
        # If there is a rebuild in progress, the document will also be added to the new index.
        tasks.append(client.index(current_rebuild_index_name).update_documents(docs))
    tasks.append(client.index(INDEX_NAME).update_documents(docs))

    _wait_for_meili_tasks(tasks)

def generate_user_token(user):
    """
    Returns a Meilisearch API key that only allows the user to search content that they have permission to view
    """
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
    search_rules = {
        INDEX_NAME: {
            # TODO: Apply filters here based on the user's permissions, so they can only search for content
            # that they have permission to view. Example:
            # 'filter': 'org = BradenX'
        }
    }
    # Note: the following is just generating a JWT. It doesn't actually make an API call to Meilisearch.
    restricted_api_key = _get_meilisearch_client().generate_tenant_token(
        api_key_uid=_get_meili_api_key_uid(),
        search_rules=search_rules,
        expires_at=expires_at,
    )

    return {
        "url": settings.MEILISEARCH_PUBLIC_URL,
        "index_name": INDEX_NAME,
        "api_key": restricted_api_key,
    }
