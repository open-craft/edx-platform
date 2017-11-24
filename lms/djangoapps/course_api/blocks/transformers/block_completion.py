"""
Block Completion Transformer
"""

from lms.djangoapps.completion.models import BlockCompletion
from openedx.core.djangoapps.content.block_structure.transformer import BlockStructureTransformer


class BlockCompletionTransformer(BlockStructureTransformer):
    """
    Keep track of the completion of each block within the block structure.
    """
    WRITE_VERSION = 1
    READ_VERSION = 1
    BLOCK_COMPLETION = 'block_completion'

    # this might be replaced with xblock.completable.CompletableXBlockMixin.{AGGREGATOR, EXCLUDED}
    # once we change requirements/base.txt to contain xblock 1.1.1
    AGGREGATOR = 'aggregator'
    EXCLUDED = 'excluded'

    def __init__(self):
        pass

    @classmethod
    def name(cls):
        return "blocks_api:block_completion"

    @classmethod
    def get_block_completion(cls, block_structure, block_key):
        """
        Return the precalculated completion of a block within the block_structure:

        Arguments:
            block_structure: a BlockStructure instance
            block_key: the key of the block whose completion we want to know

        Returns:
            block_completion: float or None
        """
        return block_structure.get_transformer_block_field(
            block_key,
            cls,
            cls.BLOCK_COMPLETION,
        )

    @classmethod
    def collect(cls, block_structure):
        block_structure.request_xblock_fields('completion_method')

    def transform(self, usage_info, block_structure):
        """
        Mutates block_structure adding extra field which contains block's completion.
        """
        def _is_block_an_aggregator_or_excluded(block_key):
            completion_method = block_structure.get_xblock_field(
                block_key, 'completion_method'
            )

            return completion_method in (self.AGGREGATOR, self.EXCLUDED)

        completions_dict = dict(
            BlockCompletion.objects.filter(
                user=usage_info.user,
                course_key=usage_info.course_key
            ).values_list(
                'block_key',
                'completion'
            )
        )

        for block_key in block_structure.topological_traversal():
            if _is_block_an_aggregator_or_excluded(block_key):
                completion_value = None
            elif block_key in completions_dict:
                completion_value = completions_dict[block_key]
            else:
                completion_value = 0.0

            block_structure.set_transformer_block_field(
                block_key, self, self.BLOCK_COMPLETION, completion_value
            )
