"""
Tests for BlockCompletionTransformer.
"""

from lms.djangoapps.completion.models import BlockCompletion
from lms.djangoapps.course_api.blocks.transformers.block_completion import BlockCompletionTransformer
from lms.djangoapps.course_blocks.transformers.tests.helpers import CourseStructureTestCase

from ...api import get_course_blocks


class BlockCompletionTransformerTestCase(CourseStructureTestCase):
    """
    Tests behaviour of BlockCompletionTransformer
    """
    TRANSFORMER_CLASS_TO_TEST = BlockCompletionTransformer
    COMPLETION_TEST_VALUE = 0.4

    def setUp(self):
        super(BlockCompletionTransformerTestCase, self).setUp()
        self.course_hierarchy = self.get_course_hierarchy()
        self.blocks = self.build_course(self.course_hierarchy)
        self.course = self.blocks['course']

        self.agg_block = self.blocks['agg']
        self.excl_block = self.blocks['excl']
        self.comp_block = self.blocks['comp']
        self.no_type_block = self.blocks['no_type']

        # create a completion for a 'comp' block of the test course
        BlockCompletion.objects.create(
            user=self.user,
            course_key=self.course.id,
            block_type=self.comp_block.location.block_type,
            block_key=self.comp_block.location,
            completion=self.COMPLETION_TEST_VALUE,
        )

        # perform
        self.block_structure = get_course_blocks(
            self.user,
            self.course.location,
            self.transformers,
        )

    def test_transform_produces_proper_completions(self):

        self._assert_block_has_proper_completion_value(
            self.agg_block.location, None
        )
        self._assert_block_has_proper_completion_value(
            self.excl_block.location, None
        )
        self._assert_block_has_proper_completion_value(
            self.comp_block.location, self.COMPLETION_TEST_VALUE
        )
        self._assert_block_has_proper_completion_value(
            self.no_type_block.location, 0.0
        )

    def _assert_block_has_proper_completion_value(self, block_key, expected_value):
        block_data = self.block_structure.get_transformer_block_data(
            block_key, self.TRANSFORMER_CLASS_TO_TEST
        )
        completion_value = block_data.fields['completion']

        self.assertEqual(completion_value, expected_value)

    def get_course_hierarchy(self):
        """
        Get a test hierarchy to test with.
        """
        #               course
        #               /   \
        #              /     \
        #            agg     excl
        #            / \
        #           /   \
        #         comp no_type

        return [
            {
                'org': 'BlockCompletionTransformer',
                'course': 'BCT-01',
                'run': 'test_run',
                '#type': 'course',
                '#ref': 'course',
            },
            {
                '#type': 'sequential',
                '#ref': 'agg',
                '#children': [
                    {'#type': 'vertical', '#ref': 'comp'},
                    {'#type': 'vertical', '#ref': 'no_type'},
                ]
            },
            {
                '#type': 'sequential',
                '#ref': 'excl'
            }
        ]
