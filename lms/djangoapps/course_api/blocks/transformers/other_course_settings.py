"""
Other Course Settings Transformer
"""
from openedx.core.djangoapps.content.block_structure.transformer import BlockStructureTransformer


class OtherCourseSettingsTransformer(BlockStructureTransformer):
    """
    Show "Other Course Settings" for "course" blocks only
    """
    WRITE_VERSION = 1
    READ_VERSION = 1
    OTHER_COURSE_SETTINGS_DATA = 'other_course_settings'

    def __init__(self, other_course_settings):
        self.other_course_settings_enabled = other_course_settings

    @classmethod
    def name(cls):
        return "blocks_api:other_course_settings"

    @classmethod
    def collect(cls, block_structure):
        """
        Collects any information that's necessary to execute this transformer's
        transform method.
        """
        block_structure.request_xblock_fields('category', 'other_course_settings')

    def transform(self, usage_info, block_structure):
        """
        Mutates block_structure based on the given usage_info.
        """
        if not self.other_course_settings_enabled:
            return

        for block_key in block_structure.topological_traversal(
            filter_func=lambda key: block_structure.get_xblock_field(key, 'category') == 'course'
        ):
            other_course_settings_data = block_structure.get_xblock_field(
                block_key,
                'other_course_settings',
                dict()
            )

            block_structure.set_transformer_block_field(
                block_key,
                self,
                self.OTHER_COURSE_SETTINGS_DATA,
                other_course_settings_data
            )
