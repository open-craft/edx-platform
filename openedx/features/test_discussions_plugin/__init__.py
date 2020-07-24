from opaque_keys.edx.keys import CourseKey
from web_fragments.fragment import Fragment

from openedx.core.djangoapps.discussions.discussions_apps import DiscussionApp
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from openedx.core.djangolib.markup import HTML, Text

class TestFragmentView(EdxFragmentView):
    def render_to_fragment(
        self,
        request,
        course_id=None,
    ):
        course_key = CourseKey.from_string(course_id)
        fragment = Fragment(
            HTML(
                """
                <main>
                    This is a test plugin for discussions.
                    <p>Course Key: {course_key}</p>
                </main>
                """
            ).format(course_key=course_key)
        )
        return fragment


class TestDiscussionsApp(DiscussionApp):
    name = "test_app"
    friendly_name = "Test app"
    tab_view = TestFragmentView()
