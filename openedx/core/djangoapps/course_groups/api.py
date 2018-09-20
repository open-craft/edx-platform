"""
course_groups API
"""
import unicodecsv
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from instructor_task.api import submit_cohort_students
from opaque_keys.edx.keys import CourseKey
from util.file import UniversalNewlineIterator, FileValidationException, store_uploaded_file, \
    course_and_time_based_filename_generator
from util.json_request import JsonResponse

from openedx.core.djangoapps.course_groups.models import CohortMembership


def add_users_to_cohorts(request, course_id):
    """
    View method that accepts an uploaded file (using key "uploaded-file")
    containing cohort assignments for users. This method spawns a celery task
    to do the assignments, and a CSV file with results is provided via data downloads.
    """
    course_key = CourseKey.from_string(course_id)

    try:
        def validator(file_storage, file_to_validate):
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

        __, filename = store_uploaded_file(
            request, 'uploaded-file', ['.csv'],
            course_and_time_based_filename_generator(course_key, "cohorts"),
            max_file_size=2000000,  # limit to 2 MB
            validator=validator
        )
        # The task will assume the default file storage.
        submit_cohort_students(request, course_key, filename)
    except (FileValidationException, PermissionDenied) as err:
        return JsonResponse({"error": unicode(err)}, status=400)

    return JsonResponse()


def remove_user_from_cohort(course_key, username):
    """
    Removes an user from a course group

    Returns 204 in case of success and 404 if user does not exist
    """
    if username is None:
        return JsonResponse({'error': "Must supply an username"}, status=400)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': "No user '{0}'".format(username)}, status=404)

    try:
        membership = CohortMembership.objects.get(user=user, course_id=course_key)
        membership.delete()
    except CohortMembership.DoesNotExist:
        pass

    return JsonResponse(status=204)
