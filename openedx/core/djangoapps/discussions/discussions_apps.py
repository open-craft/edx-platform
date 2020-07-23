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

    # Name of the discussion app for internal use
    name = None
    # Name of the discussion app that will show up in UI
    friendly_name = None
    # A list of capabilities of this discussion app that can't be
    # automatically derived
    capabilities = []
    # If the discussion app would like to provide its own view to
    # embed in the main Discussions tab, it can provide it here.
    tab_view = None
    # If the discussions apps has mounted its own urls for the tab
    # this can provide the name of that view to reverse to.
    tab_view_name = None

    @classmethod
    def is_enabled(cls, context_key):
        """
        Given a context key, this returns if the tab is enabled for the course.
        """
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
