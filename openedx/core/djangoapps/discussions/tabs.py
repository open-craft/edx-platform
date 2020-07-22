import six
from django.conf import settings
from django.utils.translation import ugettext_noop

from courseware.tabs import EnrolledTab
from xmodule.tabs import TabFragmentViewMixin
from .api.providers import get_discussion_provider


class DiscussionTab(TabFragmentViewMixin, EnrolledTab):
    """
    A tab for the cs_comments_service forums.
    """

    type = 'discussion'
    title = ugettext_noop('Discussion')
    priority = None
    view_name = 'forum_form_discussion'
    is_hideable = settings.FEATURES.get('ALLOW_HIDING_DISCUSSION_TAB', False)
    is_default = False
    body_class = 'discussion'
    online_help_token = 'discussions'

    def render_to_fragment(self, request, course, **kwargs):
        """
        Renders this tab to a web fragment.
        """
        provider = get_discussion_provider(course.id)
        return provider.tab_view.render_to_fragment(request, course_id=six.text_type(course.id), **kwargs)

    @classmethod
    def is_enabled(cls, course, user=None):
        if not super(DiscussionTab, cls).is_enabled(course, user):
            return False
        provider = get_discussion_provider(course.id)
        return provider.is_enabled(course.id)

    @property
    def uses_bootstrap(self):
        """
        Returns true if this tab is rendered with Bootstrap.
        """
        return True
