from typing import Optional

from opaque_keys.edx.keys import LearningContextKey

from openedx.core.djangoapps.discussions.api.config import get_discussion_config
from openedx.core.djangoapps.discussions.discussions_apps import DiscussionApp, DiscussionAppsPluginManager


def get_discussion_provider(context_key: LearningContextKey) -> Optional[DiscussionApp]:
    """
    Returns the discussion app provider associated with the provided context key.

    Args:
        context_key (LearningContextKey): Learning context, currently only a course
    """

    config = get_discussion_config(context_key)
    if config:
        return DiscussionAppsPluginManager.get_plugin(config.provider)
