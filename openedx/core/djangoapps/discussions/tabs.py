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
    is_hideable = settings.FEATURES.get('ALLOW_HIDING_DISCUSSION_TAB', False)
    is_default = False
    body_class = 'discussion'
    online_help_token = 'discussions'

    def __init__(self, tab_dict):
        super().__init__(tab_dict)
        self._discussion_provider = None

    def _get_discussion_provider(self, course_id):
        if not self._discussion_provider:
            self._discussion_provider = get_discussion_provider(course_id)
        return self._discussion_provider

    @property
    def link_func(self):
        def inner_link_func(course, reverse_func):
            provider = self._get_discussion_provider(course.id)
            return reverse_func(provider.tab_view_name, args=[six.text_type(course.id)])
        return inner_link_func

    def render_to_fragment(self, request, course, **kwargs):
        """
        Renders this tab to a web fragment.
        """
        provider = self._get_discussion_provider(course.id)
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
