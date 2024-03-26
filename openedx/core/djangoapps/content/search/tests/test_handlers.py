from unittest.mock import MagicMock, patch

from organizations.tests.factories import OrganizationFactory
from django.test import override_settings, LiveServerTestCase

from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangoapps.content_libraries import api as library_api
from xmodule.modulestore.tests.django_utils import TEST_DATA_SPLIT_MODULESTORE, ModuleStoreTestCase
from openedx.core.lib.blockstore_api.tests.base import BlockstoreAppTestMixin

from .. import api


@patch("openedx.core.djangoapps.content.search.api._wait_for_meili_task", new=MagicMock(return_value=None))
@patch("openedx.core.djangoapps.content.search.api.MeilisearchClient")
@override_settings(MEILISEARCH_ENABLED=True)
class TestUpdateIndexHandlers(
    ModuleStoreTestCase,
    BlockstoreAppTestMixin,
    LiveServerTestCase,
):
    """
    Test that the search index is updated when XBlocks and Library Blocks are modified
    """

    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    def setUp(self):
        super().setUp()
        # Create user
        self.user = UserFactory.create()
        self.user_id = self.user.id

        self.orgA = OrganizationFactory.create(short_name="orgA")

        self.patcher = patch("openedx.core.djangoapps.content_tagging.tasks.modulestore", return_value=self.store)
        self.addCleanup(self.patcher.stop)
        self.patcher.start()

        api.clear_meilisearch_client()  # Clear the Meilisearch client to avoid leaking state from other tests


    def test_create_delete_xblock(self, meilisearch_client):
        # Create course
        course = self.store.create_course(
            self.orgA.short_name,
            "test_course",
            "test_run",
            self.user_id,
            fields={"display_name": "Test Course"},
        )

        # Create XBlocks
        sequential = self.store.create_child(self.user_id, course.location, "sequential", "test_sequential")
        meilisearch_client.return_value.index.return_value.update_documents.assert_called_with([
            {
                'id': 'block-v1orgatest_coursetest_runtypesequentialblocktest_sequential-0cdb9395',
                'type': 'course_block',
                'usage_key': 'block-v1:orgA+test_course+test_run+type@sequential+block@test_sequential',
                'block_id': 'test_sequential',
                'display_name': 'sequential',
                'block_type': 'sequential',
                'context_key': 'course-v1:orgA+test_course+test_run',
                'org': 'orgA',
                'breadcrumbs': [{'display_name': 'Test Course'}], 'content': {}
            }
        ])
        vertical = self.store.create_child(self.user_id, sequential.location, "vertical", "test_vertical")
        meilisearch_client.return_value.index.return_value.update_documents.assert_called_with([
            {
                'id': 'block-v1orgatest_coursetest_runtypeverticalblocktest_vertical-011f143b',
                'type': 'course_block',
                'usage_key': 'block-v1:orgA+test_course+test_run+type@vertical+block@test_vertical',
                'block_id': 'test_vertical',
                'display_name': 'vertical',
                'block_type': 'vertical',
                'context_key': 'course-v1:orgA+test_course+test_run',
                'org': 'orgA',
                'breadcrumbs': [{'display_name': 'Test Course'}, {'display_name': 'sequential'}],
                'content': {}
            }
        ])

        # Update the XBlock
        sequential = self.store.get_item(sequential.location, self.user_id)  # Refresh the XBlock
        sequential.display_name = "Updated Sequential"
        self.store.update_item(sequential, self.user_id)

        meilisearch_client.return_value.index.return_value.update_documents.assert_called_with([
            {
                'id': 'block-v1orgatest_coursetest_runtypesequentialblocktest_sequential-0cdb9395',
                'type': 'course_block',
                'usage_key': 'block-v1:orgA+test_course+test_run+type@sequential+block@test_sequential',
                'block_id': 'test_sequential',
                'display_name': 'Updated Sequential',
                'block_type': 'sequential',
                'context_key': 'course-v1:orgA+test_course+test_run',
                'org': 'orgA',
                'breadcrumbs': [{'display_name': 'Test Course'}], 'content': {}
            },
            {
                'id': 'block-v1orgatest_coursetest_runtypeverticalblocktest_vertical-011f143b',
                'type': 'course_block',
                'usage_key': 'block-v1:orgA+test_course+test_run+type@vertical+block@test_vertical',
                'block_id': 'test_vertical',
                'display_name': 'vertical',
                'block_type': 'vertical',
                'context_key': 'course-v1:orgA+test_course+test_run',
                'org': 'orgA',
                'breadcrumbs': [{'display_name': 'Test Course'}, {'display_name': 'Updated Sequential'}],
                'content': {}
            }
        ])

        # Delete the XBlock
        self.store.delete_item(vertical.location, self.user_id)

        meilisearch_client.return_value.index.return_value.delete_document.assert_called_with(
            'block-v1orgatest_coursetest_runtypeverticalblocktest_vertical-011f143b'
        )


    def test_create_delete_library_block(self, meilisearch_client):
        # Create library
        library = library_api.create_library(
            org=self.orgA,
            slug="lib_a",
            title="Library Org A",
            description="This is a library from Org A",
        )

        problem = library_api.create_library_block(library.key, "problem", "Problem1")

        meilisearch_client.return_value.index.return_value.update_documents.assert_called_with([
            {
                'id': 'lborgalib_aproblemproblem1-ca3186e9',
                'type': 'library_block',
                'usage_key': 'lb:orgA:lib_a:problem:Problem1',
                'block_id': 'Problem1',
                'display_name': 'Blank Problem',
                'block_type': 'problem',
                'context_key': 'lib:orgA:lib_a',
                'org': 'orgA',
                'breadcrumbs': [{'display_name': 'Library Org A'}],
                'content': {'problem_types': [], 'capa_content': ' '}
            },
        ])

        # Delete the Library Block
        library_api.delete_library_block(problem.usage_key)

        meilisearch_client.return_value.index.return_value.delete_document.assert_called_with(
            'lborgalib_aproblemproblem1-ca3186e9'
        )
