"""
Views handling read (GET) requests for the Discussion tab and inline discussions.
"""

from openedx.core.djangoapps.discussions.discussions_apps import DiscussionApp
from .django_comment_client.utils import is_discussion_enabled
from .views import DiscussionBoardFragmentView

_ = lambda text: text


class CommentServiceDiscussionApp(DiscussionApp):
    """
    Discussuion Plugin app for cs_comments_service.
    """
    name = "cs_comments"
    friendly_name = _(u"Inbuilt Discussion Forums")

    capabilities = [

    ]
    tab_view = DiscussionBoardFragmentView()
    tab_view_name = "forum_form_discussion"

    @classmethod
    def is_enabled(cls, request=None, context_key=None, user=None):
        return is_discussion_enabled(context_key)
