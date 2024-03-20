"""
Tests for the Studio content search API.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

from django.test import override_settings

from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangolib.testing.utils import skip_unless_cms
from xmodule.modulestore.tests.django_utils import TEST_DATA_SPLIT_MODULESTORE, ModuleStoreTestCase

from .. import api

STUDIO_SEARCH_ENDPOINT_URL = "/api/content_search/v2/studio/"


class MockMeilisearchClient(MagicMock):
    """
    Mock Meilisearch client.
    """
    mock_index = MagicMock()

    def health(self):
        return True

    def get_key(self, *_, **_kwargs):
        key = types.SimpleNamespace()
        key.uid = "3203d764-370f-4e99-a917-d47ab7f29739"
        return key

    def generate_tenant_token(self, *_args, **_kwargs):
        return "token"

    def get_index(self, *_, **_kwargs):
        index = types.SimpleNamespace()
        index.created_at = "2024-01-01T00:00:00.000Z"
        return index

    def delete_index(self, *_args, **_kwargs):
        pass

    def swap_indexes(self, *_args, **_kwargs):
        pass

    def create_index(self, *_args, **_kwargs):
        pass

    def index(self, index_name):
        return self.mock_index


class MeilisearchTestMixin:
    """
    Mixin for tests that use Meilisearch.
    """

    def setUp(self):
        super().setUp()
        patcher = patch('openedx.core.djangoapps.content.search.api.MeilisearchClient', new=MockMeilisearchClient)
        self.mock_meilisearch = patcher.start()
        self.addCleanup(patcher.stop)


@skip_unless_cms
class TestSearchApi(MeilisearchTestMixin, ModuleStoreTestCase):
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

        self.api_patcher = patch("openedx.core.djangoapps.content.search.api._wait_for_meili_task", return_value=None)
        self.addCleanup(self.api_patcher.stop)
        self.api_patcher.start()

    @override_settings(MEILISEARCH_ENABLED=False)
    def test_reindex_meilisearch_disabled(self):
        with self.assertRaises(RuntimeError):
            api.rebuild_index()

    def test_reindex_meilisearch(self):
        # Create course
        course = self.store.create_course(
            "orgA",
            "test_course",
            "test_run",
            self.user_id,
            fields={"display_name": "Test Course"},
        )

        # Create XBlocks
        sequential = self.store.create_child(self.user_id, course.location, "sequential", "test_sequential")
        vertical = self.store.create_child(self.user_id, sequential.location, "vertical", "test_vertical")

        with override_settings(MEILISEARCH_ENABLED=True):
            api.rebuild_index()
            self.mock_meilisearch.mock_index.add_documents.assert_called_once_with([
                {
                    'id': 'block-v1orgatest_coursetest_runtypesequentialblocktest_sequential-a32ce3b',
                    'type': 'course_block',
                    'usage_key': 'block-v1:orgA+test_course+test_run+type@sequential+block@test_sequential',
                    'block_id': 'test_sequential',
                    'display_name': 'sequential',
                    'block_type': 'sequential',
                    'context_key': 'course-v1:orgA+test_course+test_run',
                    'org': 'orgA',
                    'breadcrumbs': [{'display_name': 'Test Course'}],
                    'content': {}
                },
                {
                    'id': 'block-v1orgatest_coursetest_runtypeverticalblocktest_vertical-f4cb441',
                    'type': 'course_block',
                    'usage_key': 'block-v1:orgA+test_course+test_run+type@vertical+block@test_vertical',
                    'block_id': 'test_vertical',
                    'display_name': 'vertical',
                    'block_type': 'vertical',
                    'context_key': 'course-v1:orgA+test_course+test_run',
                    'org': 'orgA',
                    'breadcrumbs': [
                        {'display_name': 'Test Course'},
                        {'display_name': 'sequential'}
                    ],
                    'content': {}
                }
            ])
            api.rebuild_index()
