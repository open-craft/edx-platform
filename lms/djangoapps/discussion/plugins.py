"""
Views handling read (GET) requests for the Discussion tab and inline discussions.
"""
from openedx.core.djangoapps.discussions.discussions_apps import DiscussionApp

from .django_comment_client.utils import is_discussion_enabled
from .views import DiscussionBoardFragmentView

# Make '_' a no-op so we can scrape strings. Using lambda instead of
#  `django.utils.translation.ugettext_noop` because Django cannot be imported in this file
_ = lambda text: text


class CommentServiceDiscussionApp(DiscussionApp):
    """
    Discussion Plugin app for cs_comments_service.
    """
    name = "cs_comments"
    friendly_name = _("Inbuilt Discussion Forums")

    capabilities = [

    ]
    tab_view = DiscussionBoardFragmentView()
    tab_view_name = "forum_form_discussion"

    @classmethod
    def is_enabled(cls, request=None, context_key=None, user=None):
        return is_discussion_enabled(context_key)
