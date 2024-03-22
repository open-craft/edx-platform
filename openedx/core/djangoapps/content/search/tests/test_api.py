"""
Tests for the Studio content search API.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch
from organizations.tests.factories import OrganizationFactory

import ddt
from django.test import override_settings

from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangolib.testing.utils import skip_unless_cms
from xmodule.modulestore.tests.django_utils import TEST_DATA_SPLIT_MODULESTORE, ModuleStoreTestCase
from openedx.core.djangoapps.content_libraries import api as library_api

from .. import api

STUDIO_SEARCH_ENDPOINT_URL = "/api/content_search/v2/studio/"


@ddt.ddt
@skip_unless_cms
@patch("openedx.core.djangoapps.content.search.api._wait_for_meili_task", new=MagicMock(return_value=None))
@patch("openedx.core.djangoapps.content.search.api.MeilisearchClient")
class TestSearchApi(ModuleStoreTestCase):
    """
    Tests for the Studio content search and index API.
    """

    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    def setUp(self):
        super().setUp()
        self.user = UserFactory.create()
        self.user_id = self.user.id

        self.modulestore_patcher = patch(
            "openedx.core.djangoapps.content.search.api.modulestore", return_value=self.store
        )
        self.addCleanup(self.modulestore_patcher.stop)
        self.modulestore_patcher.start()

        # Clear the Meilisearch client to avoid side effects from other tests
        api.clear_meilisearch_client()

        # Create course
        self.course = self.store.create_course(
            "org1",
            "test_course",
            "test_run",
            self.user_id,
            fields={"display_name": "Test Course"},
        )

        # Create XBlocks
        self.sequential = self.store.create_child(self.user_id, self.course.location, "sequential", "test_sequential")
        self.doc_sequential = {
            'id': 'block-v1org1test_coursetest_runtypesequentialblocktest_sequential-328de7c',
            'type': 'course_block',
            'usage_key': 'block-v1:org1+test_course+test_run+type@sequential+block@test_sequential',
            'block_id': 'test_sequential',
            'display_name': 'sequential',
            'block_type': 'sequential',
            'context_key': 'course-v1:org1+test_course+test_run',
            'org': 'org1',
            'breadcrumbs': [{'display_name': 'Test Course'}],
            'content': {}
        }
        self.store.create_child(self.user_id, self.sequential.location, "vertical", "test_vertical")
        self.doc_vertical = {
            'id': 'block-v1org1test_coursetest_runtypeverticalblocktest_vertical-020cf7c',
            'type': 'course_block',
            'usage_key': 'block-v1:org1+test_course+test_run+type@vertical+block@test_vertical',
            'block_id': 'test_vertical',
            'display_name': 'vertical',
            'block_type': 'vertical',
            'context_key': 'course-v1:org1+test_course+test_run',
            'org': 'org1',
            'breadcrumbs': [
                {'display_name': 'Test Course'},
                {'display_name': 'sequential'}
            ],
            'content': {}
        }

        # Create a content library:
        self.library = library_api.create_library(
            library_type=library_api.COMPLEX,
            org=OrganizationFactory.create(short_name="org1"),
            slug="lib",
            title="Library",
        )
        # Populate it with a problem:
        self.problem_key = library_api.create_library_block(self.library.key, "problem", "p1").usage_key
        self.doc_problem = {
            "id": "lborg1libproblemp1-5951e8e",
            "usage_key": "lb:org1:lib:problem:p1",
            "block_id": "p1",
            "display_name": "Blank Problem",
            "block_type": "problem",
            "context_key": "lib:org1:lib",
            "org": "org1",
            "breadcrumbs": [{"display_name": "Library"}],
            "content": {"problem_types": [], "capa_content": " "},
            "type": "library_block",
        }

    @override_settings(MEILISEARCH_ENABLED=False)
    def test_reindex_meilisearch_disabled(self, mock_meilisearch):
        with self.assertRaises(RuntimeError):
            api.rebuild_index()

        mock_meilisearch.return_value.swap_indexes.assert_not_called()

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_reindex_meilisearch(self, mock_meilisearch):

        api.rebuild_index()
        mock_meilisearch.return_value.index.return_value.add_documents.assert_has_calls(
            [
                call([self.doc_sequential, self.doc_vertical]),
                call([self.doc_problem]),
            ],
            any_order=True,
        )

    @ddt.data(
        True,
        False
    )
    @override_settings(MEILISEARCH_ENABLED=True)
    def test_index_xblock_metadata(self, recursive, mock_meilisearch):
        """
        Test indexing an XBlock.
        """
        api.upsert_xblock_index_doc(
            self.sequential.usage_key,
            recursive=recursive,
            update_metadata=True,
            update_tags=False,
        )

        if recursive:
            expected_docs = [self.doc_sequential, self.doc_vertical]
        else:
            expected_docs = [self.doc_sequential]

        mock_meilisearch.return_value.index.return_value.update_documents.assert_called_once_with(expected_docs)

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_delete_index_xblock(self, mock_meilisearch):
        """
        Test deleting an XBlock doc from the index.
        """
        api.delete_xblock_index_doc(self.sequential.usage_key)

        mock_meilisearch.return_value.index.return_value.delete_document.assert_called_once_with(
            self.doc_sequential['id']
        )
