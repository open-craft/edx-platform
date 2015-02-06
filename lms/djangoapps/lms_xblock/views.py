import static_replace

from functools import partial, wraps

from django.http import Http404
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.auth.decorators import login_required

from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from xmodule.x_module import STUDENT_VIEW

from xblock.runtime import Mixologist
from xblock.core import XBlock
from xblock.fields import ScopeIds


from courseware.courses import get_course_with_access
from student.models import user_by_anonymous_id, anonymous_id_for_user

from lms_xblock.runtime import LmsModuleSystem, quote_slashes
from edxmako.shortcuts import render_to_response
from edxmako.shortcuts import render_to_string

from xmodule_modifiers import wrap_xblock, request_token


# TODO: copied from lms/djangoapps/django_comment_client/forum - unify
def use_bulk_ops(view_func):
    """
    Wraps internal request handling inside a modulestore bulk op, significantly
    reducing redundant database calls.  Also converts the course_id parsed from
    the request uri to a CourseKey before passing to the view.
    """
    @wraps(view_func)
    def wrapped_view(request, course_id, *args, **kwargs):  # pylint: disable=missing-docstring
        course_key = CourseKey.from_string(course_id)
        with modulestore().bulk_operations(course_key):
            return view_func(request, course_key, *args, **kwargs)
    return wrapped_view


@use_bulk_ops
@login_required
def xblock_tab_view(request, course_key, block_type=None):
    if block_type is None:
        raise Http404

    user = request.user
    course = get_course_with_access(user, 'load', course_key, depth=2)
    target_module_class = _get_xblock_class(block_type)
    runtime = _make_runtime(request, course_key, user)
    target_module = target_module_class(runtime, {}, ScopeIds(None, block_type, None, 'ImaginaryUsageId'))
    context = {
        'body_class': 'discussion',
        'title': _("Discussion - {course_number}").format(course_number=course.display_number_with_default),
        'fragment': target_module.render(STUDENT_VIEW),
        'course': course,
        'active_page': block_type
    }
    return render_to_response("xblock_tab.html", context)


# TODO: should probably look more like lms/djangoapps/courseware/module_render.py:get_module_system_for_user
def _make_runtime(request, course_key, user):
    system = LmsModuleSystem(
        static_url=settings.STATIC_URL,
        track_function=None,
        get_module=lambda descriptor: descriptor,  # stub
        render_template=render_to_string,
        replace_urls=partial(
            static_replace.replace_static_urls,
            data_directory=None,
            course_id=course_key,
            static_asset_path=''
        ),
        user=user,
        anonymous_student_id=anonymous_id_for_user(user, course_key),
        descriptor_runtime=None,
        get_real_user=user_by_anonymous_id,
        course_id=course_key,
        wrappers=_get_wrappers(request, course_key)
    )
    return system


def _get_xblock_class(category):
    component_class = XBlock.load_class(category, select=settings.XBLOCK_SELECT_FUNCTION)
    mixologist = Mixologist(settings.XBLOCK_MIXINS)
    return mixologist.mix(component_class)


def _get_wrappers(request, course_key):
    return []
    # return [partial(
    #     wrap_xblock,
    #     'LmsRuntime',
    #     extra_data={'course-id': course_key.to_deprecated_string()},
    #     usage_id_serializer=lambda usage_id: quote_slashes(usage_id),
    #     request_token=request_token(request),
    # )]
