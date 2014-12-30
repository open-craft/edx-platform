# -*- coding: utf-8 -*-
"""
Basic unit tests for LibraryContentModule

Higher-level tests are in `cms/djangoapps/contentstore/tests/test_libraries.py`.
"""
import ddt
from xmodule.library_content_module import LibraryVersionReference
from xmodule.modulestore.tests.factories import LibraryFactory, CourseFactory, ItemFactory
from xmodule.modulestore.tests.utils import MixedSplitTestCase
from xmodule.tests import get_test_system
from xmodule.validation import StudioValidationMessage


@ddt.ddt
class TestLibraries(MixedSplitTestCase):
    """
    Basic unit tests for LibraryContentModule (library_content_module.py)
    """
    def setUp(self):
        super(TestLibraries, self).setUp()

        self.library = LibraryFactory.create(modulestore=self.store)
        self.lib_blocks = [
            ItemFactory.create(
                category="html",
                parent_location=self.library.location,
                user_id=self.user_id,
                publish_item=False,
                metadata={"data": "Hello world from block {}".format(i), },
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

        def get_module(descriptor):
            """Mocks module_system get_module function"""
            sub_module_system = get_test_system(course_id=self.course.location.course_key)
            sub_module_system.get_module = get_module
            sub_module_system.descriptor_runtime = descriptor.runtime
            descriptor.bind_for_student(sub_module_system, descriptor._field_data)  # pylint: disable=protected-access
            return descriptor

        module_system.get_module = get_module
        module.xmodule_runtime = module_system

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

    def test_validation(self):
        """
        Test that the validation method of LibraryContent blocks is working.
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
        self.lc_block.refresh_children(None, None)
        self.assertTrue(self.lc_block.validate())
