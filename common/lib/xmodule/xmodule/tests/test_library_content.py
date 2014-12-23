# -*- coding: utf-8 -*-
"""
Basic unit tests for LibraryContentModule

Higher-level tests are in `cms/djangoapps/contentstore/tests/test_libraries.py`.
"""
import ddt
from mock import Mock
from xmodule.library_content_module import LibraryVersionReference, ANY_CAPA_TYPE_VALUE
from xmodule.library_tools import LibraryToolsService
from xmodule.modulestore.tests.factories import LibraryFactory, CourseFactory, ItemFactory
from xmodule.modulestore.tests.utils import MixedSplitTestCase
from xmodule.tests import get_test_system
from xmodule.validation import StudioValidationMessage


class TestLibraries(MixedSplitTestCase):
    """
    Basic unit tests for LibraryContentModule (library_content_module.py)
    """
    def setUp(self):
        super(TestLibraries, self).setUp()

        self.tools = LibraryToolsService(self.store)
        self.library = LibraryFactory.create(modulestore=self.store)
        self.lib_blocks = [
            ItemFactory.create(
                category="html",
                parent_location=self.library.location,
                user_id=self.user_id,
                publish_item=False,
                data="Hello world from block {}".format(i),
                modulestore=self.store,
            )
            for i in range(1, 5)
        ]
        self.course = CourseFactory.create(modulestore=self.store)
        self.chapter = ItemFactory.create(
            category="chapter",
            parent_location=self.course.location,
            user_id=self.user_id,
            modulestore=self.store,
        )
        self.sequential = ItemFactory.create(
            category="sequential",
            parent_location=self.chapter.location,
            user_id=self.user_id,
            modulestore=self.store,
        )
        self.vertical = ItemFactory.create(
            category="vertical",
            parent_location=self.sequential.location,
            user_id=self.user_id,
            modulestore=self.store,
        )
        self.lc_block = ItemFactory.create(
            category="library_content",
            parent_location=self.vertical.location,
            user_id=self.user_id,
            modulestore=self.store,
            metadata={
                'max_count': 1,
                'source_libraries': [LibraryVersionReference(self.library.location.library_key)]
            }
        )

    def _bind_course_module(self, module):
        """
        Bind a module (part of self.course) so we can access student-specific data.
        """
        module_system = get_test_system(course_id=self.course.location.course_key)
        module_system.descriptor_runtime = module.runtime
        module_system._services['library_tools'] = self.tools  # pylint: disable=protected-access

        def get_module(descriptor):
            """Mocks module_system get_module function"""
            sub_module_system = get_test_system(course_id=self.course.location.course_key)
            sub_module_system.get_module = get_module
            sub_module_system.descriptor_runtime = descriptor.runtime
            descriptor.bind_for_student(sub_module_system, descriptor._field_data)  # pylint: disable=protected-access
            return descriptor

        module_system.get_module = get_module
        module.xmodule_runtime = module_system

    def _get_capa_problem_type_xml(self, *args):
        """ Helper function to create empty CAPA problem definition """
        problem = "<problem>"
        for problem_type in args:
            problem += "<{problem_type}></{problem_type}>".format(problem_type=problem_type)
        problem += "</problem>"
        return problem

    def _create_capa_problems(self):
        """
        Helper function to create a set of capa problems to test against.

        Creates four blocks total.
        """
        problem_types = [
            ["multiplechoiceresponse"], ["optionresponse"], ["optionresponse", "coderesponse"],
            ["coderesponse", "optionresponse"]
        ]
        for problem_type in problem_types:
            ItemFactory.create(
                category="problem",
                parent_location=self.library.location,
                user_id=self.user_id,
                publish_item=False,
                data=self._get_capa_problem_type_xml(*problem_type),
                modulestore=self.store,
            )

    def test_lib_content_block(self):
        """
        Test that blocks from a library are copied and added as children
        """
        # Check that the LibraryContent block has no children initially
        # Normally the children get added when the "source_libraries" setting
        # is updated, but the way we do it through a factory doesn't do that.
        self.assertEqual(len(self.lc_block.children), 0)
        # Update the LibraryContent module:
        self.lc_block.refresh_children()
        self.lc_block = self.store.get_item(self.lc_block.location)
        # Check that all blocks from the library are now children of the block:
        self.assertEqual(len(self.lc_block.children), len(self.lib_blocks))

    def test_children_seen_by_a_user(self):
        """
        Test that each student sees only one block as a child of the LibraryContent block.
        """
        self.lc_block.refresh_children()
        self.lc_block = self.store.get_item(self.lc_block.location)
        self._bind_course_module(self.lc_block)
        # Make sure the runtime knows that the block's children vary per-user:
        self.assertTrue(self.lc_block.has_dynamic_children())

        self.assertEqual(len(self.lc_block.children), len(self.lib_blocks))

        # Check how many children each user will see:
        self.assertEqual(len(self.lc_block.get_child_descriptors()), 1)
        # Check that get_content_titles() doesn't return titles for hidden/unused children
        self.assertEqual(len(self.lc_block.get_content_titles()), 1)

    def test_validation_of_course_libraries(self):
        """
        Test that the validation method of LibraryContent blocks can validate
        the source_libraries setting.
        """
        # When source_libraries is blank, the validation summary should say this block needs to be configured:
        self.lc_block.source_libraries = []
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.NOT_CONFIGURED, result.summary.type)

        # When source_libraries references a non-existent library, we should get an error:
        self.lc_block.source_libraries = [LibraryVersionReference("library-v1:BAD+WOLF")]
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.ERROR, result.summary.type)
        self.assertIn("invalid", result.summary.text)

        # When source_libraries is set but the block needs to be updated, the summary should say so:
        self.lc_block.source_libraries = [LibraryVersionReference(self.library.location.library_key)]
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.WARNING, result.summary.type)
        self.assertIn("out of date", result.summary.text)

        # Now if we update the block, all validation should pass:
        self.lc_block.refresh_children()
        self.assertTrue(self.lc_block.validate())

    def test_validation_of_matching_blocks(self):
        """
        Test that the validation method of LibraryContent blocks can warn
        the user about problems with other settings (max_count and capa_type).
        """
        # Set max_count to higher value than exists in library
        self.lc_block.max_count = 50
        self.lc_block.refresh_children()  # In the normal studio editing process, editor_saved() calls refresh_children at this point
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.WARNING, result.summary.type)
        self.assertIn("only 4 matching problems", result.summary.text)

        # Add some capa problems so we can check problem type validation messages
        self.lc_block.max_count = 1
        self._create_capa_problems()
        self.lc_block.refresh_children()
        self.assertTrue(self.lc_block.validate())

        # Existing problem type should pass validation
        self.lc_block.max_count = 1
        self.lc_block.capa_type = 'multiplechoiceresponse'
        self.lc_block.refresh_children()
        self.assertTrue(self.lc_block.validate())

        # ... unless requested more blocks than exists in library
        self.lc_block.max_count = 10
        self.lc_block.capa_type = 'multiplechoiceresponse'
        self.lc_block.refresh_children()
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.WARNING, result.summary.type)
        self.assertIn("only 1 matching problem", result.summary.text)

        # Missing problem type should always fail validation
        self.lc_block.max_count = 1
        self.lc_block.capa_type = 'customresponse'
        self.lc_block.refresh_children()
        result = self.lc_block.validate()
        self.assertFalse(result)  # Validation fails due to at least one warning/message
        self.assertTrue(result.summary)
        self.assertEqual(StudioValidationMessage.WARNING, result.summary.type)
        self.assertIn("no matching problem types", result.summary.text)

    def test_capa_type_filtering(self):
        """
        Test that the capa type filter is actually filtering children
        """
        self._create_capa_problems()
        self.assertEqual(len(self.lc_block.children), 0)  # precondition check
        self.lc_block.capa_type = "multiplechoiceresponse"
        self.lc_block.refresh_children()
        self.assertEqual(len(self.lc_block.children), 1)

        self.lc_block.capa_type = "optionresponse"
        self.lc_block.refresh_children()
        self.assertEqual(len(self.lc_block.children), 3)

        self.lc_block.capa_type = "coderesponse"
        self.lc_block.refresh_children()
        self.assertEqual(len(self.lc_block.children), 2)

        self.lc_block.capa_type = "customresponse"
        self.lc_block.refresh_children()
        self.assertEqual(len(self.lc_block.children), 0)

        self.lc_block.capa_type = ANY_CAPA_TYPE_VALUE
        self.lc_block.refresh_children()
        self.assertEqual(len(self.lc_block.children), len(self.lib_blocks) + 4)

    def test_get_block_original_usage(self):
        """
        Test that the get_block_original_usage() method of library_tools works.
        """
        original_keys = set([block.location for block in self.lib_blocks])
        self.lc_block.max_count = 5000
        self.lc_block = self.store.update_item(self.lc_block, self.user_id)
        self.lc_block.refresh_children()
        self.lc_block = self.store.get_item(self.lc_block.location)
        self._bind_course_module(self.lc_block)
        new_keys = set([block.location for block in self.lc_block.get_child_descriptors()])

        retrieved_original_keys = set([self.tools.get_block_original_usage(key) for key in new_keys])
        self.assertEqual(len(retrieved_original_keys), len(self.lib_blocks))
        self.assertEqual(original_keys, retrieved_original_keys)

    def test_analytics(self):
        """
        Test that analytics logging happens as students are assigned blocks.
        """
        publisher = Mock()
        self.lc_block.refresh_children()
        self.lc_block = self.store.get_item(self.lc_block.location)
        self._bind_course_module(self.lc_block)
        self.lc_block.xmodule_runtime.publish = publisher

        child = self.lc_block.get_child_descriptors()[0]
        child_lib_location = self.tools.get_block_original_usage(child.location)
        self.assertTrue(publisher.called)
        self.assertTrue(len(publisher.call_args[0]), 3)
        _, event_name, event_data = publisher.call_args[0]
        self.assertEqual(event_name, "edx.librarycontentblock.content.assigned")
        self.assertEqual(event_data, {
            "location": unicode(self.lc_block.location),
            "added": [(unicode(child.location), unicode(child_lib_location))],
            "result": [(unicode(child.location), unicode(child_lib_location))],
        })
        publisher.reset_mock()

        # Now increase max_count so that one more child will be added:
        self.lc_block.max_count = 2
        del self.lc_block._xmodule._selected_set  # Clear the cache (only needed because we skip saving/re-loading the block) pylint: disable=protected-access
        children = self.lc_block.get_child_descriptors()
        self.assertEqual(len(children), 2)
        child, new_child = children if children[0].location == child.location else reversed(children)
        self.assertTrue(publisher.called)
        self.assertTrue(len(publisher.call_args[0]), 3)
        _, event_name, event_data = publisher.call_args[0]
        self.assertEqual(event_name, "edx.librarycontentblock.content.assigned")
        self.assertEqual(event_data["added"][0][0], unicode(new_child.location))
        self.assertEqual(len(event_data["result"]), 2)
        publisher.reset_mock()

        # Now decrease max_count and look for the corresponding event:
        self.lc_block.max_count = 1
        del self.lc_block._xmodule._selected_set  # Clear the cache (only needed because we skip saving/re-loading the block) pylint: disable=protected-access

        def check_remove_event(num_children_left, num_removed, reason):
            """ Check that num_removed blocks were removed, leaving num_children_left, for reason """
            children = self.lc_block.get_child_descriptors()
            self.assertEqual(len(children), num_children_left)
            self.assertTrue(publisher.called)
            self.assertTrue(len(publisher.call_args[0]), 3)
            _, event_name, event_data = publisher.call_args[0]
            self.assertEqual(event_name, "edx.librarycontentblock.content.removed")
            self.assertEqual(event_data["location"], unicode(self.lc_block.location))
            self.assertEqual(len(event_data["blocks"]), num_removed)
            self.assertEqual(event_data["reason"], reason)
        check_remove_event(num_children_left=1, num_removed=1, reason="overlimit")
        publisher.reset_mock()

        # Now change source_libraries and look for the corresponding event:
        self.lc_block.source_libraries = []
        self.lc_block.children = []  # Manually delete the children here because refresh_children in this test environment will lose our student state
        del self.lc_block._xmodule._selected_set  # Clear the cache (only needed because we skip saving/re-loading the block) pylint: disable=protected-access
        check_remove_event(num_children_left=0, num_removed=1, reason="invalid")
