from typing import List, Optional

from opaque_keys.edx.keys import LearningContextKey

from .data import DiscussionConfigData
from ..models import DiscussionConfig, LearningContextDiscussionConfig


def get_discussion_config_options(context_key: LearningContextKey) -> List[DiscussionConfigData]:
    """
    Returns the available discussion configuration options for provided context.

    Args:
        context_key (LearningContextKey): Learning context, currently only a course

    Returns:
        A list of :class:`DiscussionConfigData` objects.

    """
    return [
        DiscussionConfigData(
            provider=discussion_config.provider,
            slug=discussion_config.slug,
            config=discussion_config.config,
            private_config=discussion_config.private_config,
        )
        for discussion_config in DiscussionConfig.available(context_key=context_key)
    ]


def get_discussion_config(context_key: LearningContextKey) -> Optional[DiscussionConfigData]:
    """
    Returns the active discussion configuration for the context.

    Args:
        context_key (LearningContextKey): Learning context, currently only a course

    Returns:
        A :class:`DiscussionConfigData` object with the active configuration for this course.
        Returns `None` if a discussion tool isn't configures for the course yet, of if it is disabled.

    """
    # TODO: Check if discussion_enabled is set for the course. If not return None.
    try:
        slug = LearningContextDiscussionConfig.objects.get(pk=context_key).config_slug
    except LearningContextDiscussionConfig.DoesNotExist:
        return
    discussion_config = DiscussionConfig.current(context_key=context_key, slug=slug)
    return DiscussionConfigData(
        provider=discussion_config.provider,
        slug=discussion_config.slug,
        config=discussion_config.config,
        private_config=discussion_config.private_config,
    )
