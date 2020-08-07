from lti_consumer.lti_1p1.contrib.django import lti_embed
from opaque_keys.edx.keys import CourseKey
from web_fragments.fragment import Fragment

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from openedx.core.djangolib.markup import HTML


class PiazzaDiscussionFragmentView(EdxFragmentView):
    DISCUSSION_APP_PROVIDER = "piazza"
    LTI_LAUNCH_URL = "https://piazza.com/connect"

    def render_to_fragment(
        self,
        request,
        course_id=None,
    ):
        # course_id is a string
        course_key = CourseKey.from_string(course_id)

        # IMPORTANT: Do not import this method in the top level of this file as it
        #   will cause a circular import issue. Instead, import it only at the last moment
        from openedx.core.djangoapps.discussions.api.config import get_discussion_config
        discussion_config = get_discussion_config(course_key)

        assert discussion_config.provider == self.DISCUSSION_APP_PROVIDER, "Discussion Config Provider is not Piazza"

        course = CourseOverview.get_from_id(course_key)

        resource_link_id = str(course_key.make_usage_key('course', course_key.run))
        user_id = str(request.user.id)
        result_sourcedid = "_".join([resource_link_id, user_id])

        fragment = Fragment(
            HTML(
                lti_embed(
                    html_element_id='piazza-discussion-lti-embed',
                    lti_launch_url=self.LTI_LAUNCH_URL,
                    oauth_key=discussion_config.private_config["oauth_key"],
                    oauth_secret=discussion_config.private_config["oauth_secret"],
                    resource_link_id=resource_link_id,
                    user_id=user_id,
                    roles='Student',  # TODO Use API for this when available
                    context_id=course_id,  # TODO Use API for this when available
                    context_title=course.display_name_with_default,
                    context_label=course.display_org_with_default,
                    result_sourcedid=result_sourcedid
                )
            )
        )
        return fragment
