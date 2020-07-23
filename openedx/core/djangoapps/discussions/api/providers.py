from typing import List, Optional

from opaque_keys.edx.keys import LearningContextKey

from .config import get_discussion_config
from ..discussions_apps import DiscussionApp, DiscussionAppsPluginManager


def get_discussion_provider(context_key: LearningContextKey) -> Optional[DiscussionApp]:
    """
    Returns the discussion app provider associated with the provided context key.

    Args:
        context_key (LearningContextKey): Learning context, currently only a course

    Returns:
        A DiscussionApp instance for the discussion provider associated with this context.
    """

    config = get_discussion_config(context_key)
    if config:
        return DiscussionAppsPluginManager.get_plugin(config.provider)


def get_available_discussion_providers() -> List[DiscussionApp]:
    """
    Returns a list of all supported discussion providers.
    """
    return DiscussionAppsPluginManager.get_enabled_discussion_apps()
