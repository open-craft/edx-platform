"""
Cohort API
"""

from django.db import transaction
from django.views.decorators.http import require_POST
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course_with_access
from lms.djangoapps.instructor.views.api import _add_users_to_cohorts
from openedx.core.djangoapps.course_groups.views import _course_cohort_settings_handler, _cohort_handler, \
    _add_users_to_cohort, _users_in_cohort, _remove_user_from_cohort
from openedx.core.lib.api.view_utils import view_auth_classes


@view_auth_classes()
def course_cohort_settings_handler(request, course_key_string):
    """
    OAuth2 endpoint for cohort settings.
    """
    return _course_cohort_settings_handler(request, course_key_string)


@view_auth_classes()
def cohort_handler(request, course_key_string, cohort_id=None):
    """
    OAuth2 endpoint for cohort handler.
    """
    return _cohort_handler(request, course_key_string, cohort_id)


@view_auth_classes()
def users_in_cohort(request, course_key_string, cohort_id):
    """
    OAuth2 endpoint for fetching users in a cohort.
    """
    return _users_in_cohort(request, course_key_string, cohort_id)


@view_auth_classes()
def add_users_to_cohort(request, course_key_string, cohort_id):
    """
    OAuth2 endpoint for adding users to a cohort.
    """
    return _add_users_to_cohort(request, course_key_string, cohort_id)


@view_auth_classes()
def remove_user_from_cohort(request, course_key_string, cohort_id):
    """
    OAuth2 endpoint for removing an user from a cohort.
    """
    return _remove_user_from_cohort(request, course_key_string, cohort_id)


@transaction.non_atomic_requests
@require_POST
@view_auth_classes()
def add_users_from_csv(request, course_key_string):
    """
    OAuth2 endpoint for adding user to cohorts using csv.
    """
    get_course_with_access(request.user, 'staff', CourseKey.from_string(course_key_string))
    return _add_users_to_cohorts(request, course_key_string)
