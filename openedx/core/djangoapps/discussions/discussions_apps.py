from django.conf import settings

from openedx.core.lib.plugins import PluginManager

DISCUSSION_APPS_NAMESPACE = 'openedx.discussion_apps'


class DiscussionAppCapabilities:
    """ Enum that lists capabilities supported by a discussion tool. """
    LTI1p1 = u"lti1.1"
    LTI1p3 = u"lti1.3"
    IN_CONTEXT_DISCUSSIONS = u"in_context_discussions"
    NOTIFICATIONS = u"notifications"
    COHORTS = u"cohort_aware"


class DiscussionApp:
    """
    Optional base class for discussion apps.
    """

    name = None
    friendly_name = None
    use_common_discussion_tab = True
    capabilities = []
    tab_view = None

    @classmethod
    def is_enabled(cls, context_key):
        return True


class DiscussionAppsPluginManager(PluginManager):
    """
    Manager for all of the course tools that have been made available.

    Course tool implementation can subclass `CourseTool` or can implement
    the required class methods themselves.
    """
    NAMESPACE = DISCUSSION_APPS_NAMESPACE

    @classmethod
    def get_discussion_apps(cls):
        """
        Returns the list of available course tools in their canonical order.
        """
        discussion_apps = list(cls.get_available_plugins().values())
        return discussion_apps

    @classmethod
    def get_enabled_discussion_apps(cls, request, course_key):
        """
        Returns the course tools applicable to the current user and course.
        """
        discussion_apps = cls.get_discussion_apps()
        return [
            tool
            for tool in discussion_apps
            if tool.name in settings.ENABLED_DISCUSSION_PROVIDERS
            and tool.is_enabled(request, course_key)
        ]
