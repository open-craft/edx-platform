"""
Tests for the Studio content search documents (what gets stored in the index)
"""
from organizations.models import Organization
from openedx.core.djangoapps.content_tagging import api as tagging_api
from openedx.core.djangolib.testing.utils import skip_unless_cms
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import BlockFactory, ToyCourseFactory

try:
    # This import errors in the lms because content.search is not an installed app there.
    from ..documents import searchable_doc_for_course_block
    from ..models import SearchAccess
except RuntimeError:
    searchable_doc_for_course_block = lambda x: x
    SearchAccess = {}


STUDIO_SEARCH_ENDPOINT_URL = "/api/content_search/v2/studio/"


@skip_unless_cms
class StudioDocumentsTest(SharedModuleStoreTestCase):
    """
    Tests for the Studio content search documents (what gets stored in the
    search index)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = modulestore()
        cls.toy_course = ToyCourseFactory.create()  # See xmodule/modulestore/tests/sample_courses.py
        cls.toy_course_key = cls.toy_course.id
        cls.toy_course_access_id = SearchAccess.objects.get(context_key=cls.toy_course_key).id

        # Get references to some blocks in the toy course
        cls.html_block_key = cls.toy_course_key.make_usage_key("html", "toyjumpto")
        # Create a problem in library
        cls.problem_block = BlockFactory.create(
            category="problem",
            parent_location=cls.toy_course_key.make_usage_key("vertical", "vertical_test"),
            display_name='Test Problem',
            data="<problem>What is a test?<multiplechoiceresponse></multiplechoiceresponse></problem>",
        )

        # Create a couple taxonomies and some tags
        cls.org = Organization.objects.create(name="edX", short_name="edX")
        cls.difficulty_tags = tagging_api.create_taxonomy(name="Difficulty", orgs=[cls.org], allow_multiple=False)
        tagging_api.add_tag_to_taxonomy(cls.difficulty_tags, tag="Easy")
        tagging_api.add_tag_to_taxonomy(cls.difficulty_tags, tag="Normal")
        tagging_api.add_tag_to_taxonomy(cls.difficulty_tags, tag="Difficult")

        cls.subject_tags = tagging_api.create_taxonomy(name="Subject", orgs=[cls.org], allow_multiple=True)
        tagging_api.add_tag_to_taxonomy(cls.subject_tags, tag="Linguistics")
        tagging_api.add_tag_to_taxonomy(cls.subject_tags, tag="Asian Languages", parent_tag_value="Linguistics")
        tagging_api.add_tag_to_taxonomy(cls.subject_tags, tag="Chinese", parent_tag_value="Asian Languages")
        tagging_api.add_tag_to_taxonomy(cls.subject_tags, tag="Hypertext")
        tagging_api.add_tag_to_taxonomy(cls.subject_tags, tag="Jump Links", parent_tag_value="Hypertext")

        # Tag stuff:
        tagging_api.tag_object(str(cls.problem_block.usage_key), cls.difficulty_tags, tags=["Easy"])
        tagging_api.tag_object(str(cls.html_block_key), cls.subject_tags, tags=["Chinese", "Jump Links"])
        tagging_api.tag_object(str(cls.html_block_key), cls.difficulty_tags, tags=["Normal"])

    def test_problem_block(self):
        """
        Test how a problem block gets represented in the search index
        """
        block = self.store.get_item(self.problem_block.usage_key)
        doc = searchable_doc_for_course_block(block)
        assert doc == {
            # Note the 'id' has been stripped of special characters to meet Meilisearch requirements.
            # The '-8516ed8' suffix is deterministic based on the original usage key.
            "id": "block-v1edxtoy2012_falltypeproblemblocktest_problem-f46b6f1e",
            "type": "course_block",
            "block_type": "problem",
            "usage_key": "block-v1:edX+toy+2012_Fall+type@problem+block@Test_Problem",
            "block_id": "Test_Problem",
            "context_key": "course-v1:edX+toy+2012_Fall",
            "org": "edX",
            "access_id": self.toy_course_access_id,
            "display_name": "Test Problem",
            "breadcrumbs": [
                {"display_name": "Toy Course"},
                {"display_name": "chapter"},
                {"display_name": "sequential"},
                {"display_name": "vertical"},
            ],
            "content": {
                "capa_content": "What is a test?",
                "problem_types": ["multiplechoiceresponse"],
            },
            # See https://blog.meilisearch.com/nested-hierarchical-facets-guide/
            # and https://www.algolia.com/doc/api-reference/widgets/hierarchical-menu/js/
            # For details on why the hierarchical tag data is in this format.
            "tags": {
                "taxonomy": ["Difficulty"],
                "level0": ["Difficulty > Easy"],
            },
        }

    def test_html_block(self):
        """
        Test how an HTML block gets represented in the search index
        """
        block = self.store.get_item(self.html_block_key)
        doc = searchable_doc_for_course_block(block)
        assert doc == {
            "id": "block-v1edxtoy2012_falltypehtmlblocktoyjumpto-efb9c601",
            "type": "course_block",
            "block_type": "html",
            "usage_key": "block-v1:edX+toy+2012_Fall+type@html+block@toyjumpto",
            "block_id": "toyjumpto",
            "context_key": "course-v1:edX+toy+2012_Fall",
            "org": "edX",
            "access_id": self.toy_course_access_id,
            "display_name": "Text",
            "breadcrumbs": [
                {"display_name": "Toy Course"},
                {"display_name": "Overview"},
                {"display_name": "Toy Videos"},
            ],
            "content": {
                "html_content": (
                    "This is a link to another page and some Chinese 四節比分和七年前 Some more Chinese 四節比分和七年前 "
                ),
            },
            "tags": {
                "taxonomy": ["Difficulty", "Subject"],
                "level0": ["Difficulty > Normal", "Subject > Hypertext", "Subject > Linguistics"],
                "level1": ["Subject > Hypertext > Jump Links", "Subject > Linguistics > Asian Languages"],
                "level2": ["Subject > Linguistics > Asian Languages > Chinese"],
            },
        }

    def test_video_block_untagged(self):
        """
        Test how a video block gets represented in the search index.
        """
        block_usage_key = self.toy_course_key.make_usage_key("video", "Welcome")
        block = self.store.get_item(block_usage_key)
        doc = searchable_doc_for_course_block(block)
        assert doc == {
            "id": "block-v1edxtoy2012_falltypevideoblockwelcome-0c9fd626",
            "type": "course_block",
            "block_type": "video",
            "usage_key": "block-v1:edX+toy+2012_Fall+type@video+block@Welcome",
            "block_id": "Welcome",
            "context_key": "course-v1:edX+toy+2012_Fall",
            "org": "edX",
            "access_id": self.toy_course_access_id,
            "display_name": "Welcome",
            "breadcrumbs": [
                {"display_name": "Toy Course"},
                {"display_name": "Overview"},
            ],
            "content": {},
            # This video has no tags.
        }
