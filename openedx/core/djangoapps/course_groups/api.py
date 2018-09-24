"""
course_groups API
"""
import re
import unicodecsv
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import ugettext as _
from instructor_task.api import submit_cohort_students
from opaque_keys.edx.keys import CourseKey
from util.file import UniversalNewlineIterator, FileValidationException, store_uploaded_file, \
    course_and_time_based_filename_generator
from util.json_request import JsonResponse

from openedx.core.djangoapps.course_groups.models import CohortMembership

from . import cohorts


def split_by_comma_and_whitespace(cstr):
    """
    Split a string both by commas and whitespace.  Returns a list.
    """
    return re.split(r'[\s,]+', cstr)


def _csv_validator(file_storage, file_to_validate):
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


def add_users_to_cohort(cohort, users):
    """
    Adds the given comma/space separated usernames/email addresses to the given cohort.
    """
    added = []
    changed = []
    present = []
    unknown = []
    preassigned = []
    invalid = []
    for username_or_email in split_by_comma_and_whitespace(users):
        if not username_or_email:
            continue

        try:
            # A user object is only returned by add_user_to_cohort if the user already exists.
            (user, previous_cohort, preassignedCohort) = cohorts.add_user_to_cohort(cohort, username_or_email)

            if preassignedCohort:
                preassigned.append(username_or_email)
            elif previous_cohort:
                info = {'email': user.email,
                        'previous_cohort': previous_cohort,
                        'username': user.username}
                changed.append(info)
            else:
                info = {'username': user.username,
                        'email': user.email}
                added.append(info)
        except User.DoesNotExist:
            unknown.append(username_or_email)
        except ValidationError:
            invalid.append(username_or_email)
        except ValueError:
            present.append(username_or_email)

    return {
        'added': added,
        'changed': changed,
        'present': present,
        'unknown': unknown,
        'preassigned': preassigned,
        'invalid': invalid
    }


def add_users_to_cohorts(request, course_id):
    """
    View method that accepts an uploaded file (using key "uploaded-file")
    containing cohort assignments for users. This method spawns a celery task
    to do the assignments, and a CSV file with results is provided via data downloads.
    """
    course_key = CourseKey.from_string(course_id)

    try:
        __, filename = store_uploaded_file(
            request, 'uploaded-file', ['.csv'],
            course_and_time_based_filename_generator(course_key, "cohorts"),
            max_file_size=2000000,  # limit to 2 MB
            validator=_csv_validator
        )
        # The task will assume the default file storage.
        submit_cohort_students(request, course_key, filename)
    except (FileValidationException, PermissionDenied) as err:
        return JsonResponse({"error": unicode(err)}, status=400)

    return JsonResponse()


def remove_user_from_cohort(course_key, username):
    """
    Removes an user from a course group.
    """
    if username is None:
        raise ValueError('Need a valid username')
    user = User.objects.get(username=username)
    membership = CohortMembership.objects.get(user=user, course_id=course_key)
    membership.delete()
