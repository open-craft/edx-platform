"""
Tests for OtherCourseSettingsTransformer.
"""
import unittest

# pylint: disable=protected-access
from openedx.core.djangoapps.content.block_structure.factory import BlockStructureFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import SampleCourseFactory

from ..other_course_settings import OtherCourseSettingsTransformer


class TestOtherCourseSettingsTransformer(ModuleStoreTestCase):
    """
    Test proper behavior for OtherCourseSettingsTransformer
    """
    shard = 4

    def setUp(self):
        super(TestOtherCourseSettingsTransformer, self).setUp()
        self.course_key = SampleCourseFactory.create().id
        self.course_usage_key = self.store.make_course_usage_key(self.course_key)
        self.block_structure = BlockStructureFactory.create_from_modulestore(self.course_usage_key, self.store)

    def test_transform(self):
        # collect phase
        OtherCourseSettingsTransformer.collect(self.block_structure)
        self.block_structure._collect_requested_xblock_fields()

        # transform phase
        OtherCourseSettingsTransformer(other_course_settings=True).transform(
            usage_info=None,
            block_structure=self.block_structure,
        )

        block_data = self.block_structure.get_transformer_block_data(
            self.course_usage_key, OtherCourseSettingsTransformer,
        )

        self.assertEquals(block_data.other_course_settings, dict())
