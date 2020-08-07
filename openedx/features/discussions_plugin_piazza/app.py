from openedx.core.djangoapps.discussions.discussions_apps import (
    DiscussionApp,
    DiscussionAppCapabilities
)

from .views import PiazzaDiscussionFragmentView


class PiazzaDiscussionApp(DiscussionApp):
    """
    Discussion Plugin app for Piazza.
    """
    name = "piazza"
    friendly_name = "Piazza LTI Discussion Forums"

    capabilities = [
        DiscussionAppCapabilities.LTI1p1,
    ]
    tab_view = PiazzaDiscussionFragmentView()
