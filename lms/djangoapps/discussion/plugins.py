"""
Views handling read (GET) requests for the Discussion tab and inline discussions.
"""

import lms.djangoapps.discussion.django_comment_client.utils as utils
from discussion.views import DiscussionBoardFragmentView
from openedx.core.djangoapps.discussions.discussions_apps import DiscussionApp

_ = lambda text: text


class CommentServiceDiscussionApp(DiscussionApp):
    friendly_name = _(u"Inbuilt Discussion Forums")

    capabilities = [

    ]
    tab_view = DiscussionBoardFragmentView()
    #'discussion.views.DiscussionBoardFragmentView'

    @classmethod
    def is_enabled(cls, context_key, user=None):
        return utils.is_discussion_enabled(context_key)
