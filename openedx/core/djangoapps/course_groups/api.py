"""
course_groups API
"""
import unicodecsv
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from opaque_keys.edx.keys import CourseKey
from util.file import UniversalNewlineIterator, FileValidationException

from lms.djangoapps.courseware.courses import get_course_with_access
from openedx.core.djangoapps.course_groups.models import CohortMembership


def csv_validator(file_storage, file_to_validate):
    """
    Verifies that the expected columns are present.
    """
    with file_storage.open(file_to_validate) as f:
        reader = unicodecsv.reader(UniversalNewlineIterator(f), encoding='utf-8')
        try:
            fieldnames = next(reader)
        except StopIteration:
            fieldnames = []
        msg = None
        if "cohort" not in fieldnames:
            msg = _("The file must contain a 'cohort' column containing cohort names.")
        elif "email" not in fieldnames and "username" not in fieldnames:
            msg = _("The file must contain a 'username' column, an 'email' column, or both.")
        if msg:
            raise FileValidationException(msg)


def remove_user_from_cohort(course_key, username):
    """
    Removes an user from a course group.
    """
    if username is None:
        raise ValueError('Need a valid username')
    user = User.objects.get(username=username)
    membership = CohortMembership.objects.get(user=user, course_id=course_key)
    membership.delete()


def get_course(request, course_key_string, action='staff'):
    """
    Fetching a course with expected permission level

    :param request: Django request for fetching the current user
    :param course_key_string: String representation of the course key
    :param action: Access level expected
    :return: The course and its key
    """
    course_key = CourseKey.from_string(course_key_string)
    return course_key, get_course_with_access(request.user, action, course_key)
