"""
Views related to course groups functionality.
"""

import logging
import re

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.urls import reverse
from django.http import Http404, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from edx_rest_framework_extensions.authentication import JwtAuthentication
from opaque_keys.edx.keys import CourseKey
from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_oauth.authentication import OAuth2Authentication
from six import text_type

from courseware.courses import get_course_with_access
from edxmako.shortcuts import render_to_response
from util.file import FileValidationException, store_uploaded_file, course_and_time_based_filename_generator
from util.json_request import JsonResponse, expect_json

from instructor_task.api_helper import submit_task
from instructor_task.tasks import cohort_students
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin
from . import api, cohorts
from .models import CohortMembership, CourseUserGroup, CourseUserGroupPartitionGroup

log = logging.getLogger(__name__)


def json_http_response(data):
    """
    Return an HttpResponse with the data json-serialized and the right content
    type header.
    """
    return JsonResponse(data)


def split_by_comma_and_whitespace(cstr):
    """
    Split a string both by commas and whitespace.  Returns a list.
    """
    return re.split(r'[\s,]+', cstr)


def link_cohort_to_partition_group(cohort, partition_id, group_id):
    """
    Create cohort to partition_id/group_id link.
    """
    CourseUserGroupPartitionGroup(
        course_user_group=cohort,
        partition_id=partition_id,
        group_id=group_id,
    ).save()


def unlink_cohort_partition_group(cohort):
    """
    Remove any existing cohort to partition_id/group_id link.
    """
    CourseUserGroupPartitionGroup.objects.filter(course_user_group=cohort).delete()


# pylint: disable=invalid-name
def _get_course_cohort_settings_representation(cohort_id, is_cohorted):
    """
    Returns a JSON representation of a course cohort settings.
    """
    return {
        'id': cohort_id,
        'is_cohorted': is_cohorted,
    }


def _cohort_settings(course_key):
    """
    Fetch a course current cohort settings.
    """
    return _get_course_cohort_settings_representation(
        cohorts.get_course_cohort_id(course_key),
        cohorts.is_course_cohorted(course_key)
    )


def _get_cohort_representation(cohort, course):
    """
    Returns a JSON representation of a cohort.
    """
    group_id, partition_id = cohorts.get_group_info_for_cohort(cohort)
    assignment_type = cohorts.get_assignment_type(cohort)
    return {
        'name': cohort.name,
        'id': cohort.id,
        'user_count': cohort.users.filter(courseenrollment__course_id=course.location.course_key,
                                          courseenrollment__is_active=1).count(),
        'assignment_type': assignment_type,
        'user_partition_id': partition_id,
        'group_id': group_id,
    }


@require_http_methods(("GET", "PATCH"))
@ensure_csrf_cookie
@expect_json
@login_required
def course_cohort_settings_handler(request, course_key_string):
    """
    The restful handler for cohort setting requests. Requires JSON.
    This will raise 404 if user is not staff.
    GET
        Returns the JSON representation of cohort settings for the course.
    PATCH
        Updates the cohort settings for the course. Returns the JSON representation of updated settings.
    """
    course_key = CourseKey.from_string(course_key_string)
    # Although this course data is not used this method will return 404 is user is not staff
    get_course_with_access(request.user, 'staff', course_key)

    if request.method == 'PATCH':
        if 'is_cohorted' not in request.json:
            return JsonResponse({"error": unicode("Bad Request")}, 400)

        is_cohorted = request.json.get('is_cohorted')
        try:
            cohorts.set_course_cohorted(course_key, is_cohorted)
        except ValueError as err:
            # Note: error message not translated because it is not exposed to the user (UI prevents this state).
            return JsonResponse({"error": unicode(err)}, 400)

    return JsonResponse(_get_course_cohort_settings_representation(
        cohorts.get_course_cohort_id(course_key),
        cohorts.is_course_cohorted(course_key)
    ))


@require_http_methods(("GET", "PUT", "POST", "PATCH"))
@ensure_csrf_cookie
@expect_json
@login_required
def cohort_handler(request, course_key_string, cohort_id=None):
    """
    The restful handler for cohort requests. Requires JSON.
    GET
        If a cohort ID is specified, returns a JSON representation of the cohort
            (name, id, user_count, assignment_type, user_partition_id, group_id).
        If no cohort ID is specified, returns the JSON representation of all cohorts.
           This is returned as a dict with the list of cohort information stored under the
           key `cohorts`.
    PUT or POST or PATCH
        If a cohort ID is specified, updates the cohort with the specified ID. Currently the only
        properties that can be updated are `name`, `user_partition_id` and `group_id`.
        Returns the JSON representation of the updated cohort.
        If no cohort ID is specified, creates a new cohort and returns the JSON representation of the updated
        cohort.
    """
    course_key = CourseKey.from_string(course_key_string)
    course = get_course_with_access(request.user, 'staff', course_key)
    if request.method == 'GET':
        if not cohort_id:
            all_cohorts = [
                _get_cohort_representation(c, course)
                for c in cohorts.get_course_cohorts(course)
            ]
            return JsonResponse({'cohorts': all_cohorts})
        else:
            cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
            return JsonResponse(_get_cohort_representation(cohort, course))
    else:
        name = request.json.get('name')
        assignment_type = request.json.get('assignment_type')
        if not name:
            # Note: error message not translated because it is not exposed to the user (UI prevents this state).
            return JsonResponse({"error": "Cohort name must be specified."}, 400)
        if not assignment_type:
            # Note: error message not translated because it is not exposed to the user (UI prevents this state).
            return JsonResponse({"error": "Assignment type must be specified."}, 400)
        # If cohort_id is specified, update the existing cohort. Otherwise, create a new cohort.
        if cohort_id:
            cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
            if name != cohort.name:
                if cohorts.is_cohort_exists(course_key, name):
                    err_msg = ugettext("A cohort with the same name already exists.")
                    return JsonResponse({"error": unicode(err_msg)}, 400)
                cohort.name = name
                cohort.save()
            try:
                cohorts.set_assignment_type(cohort, assignment_type)
            except ValueError as err:
                return JsonResponse({"error": unicode(err)}, 400)
        else:
            try:
                cohort = cohorts.add_cohort(course_key, name, assignment_type)
            except ValueError as err:
                return JsonResponse({"error": unicode(err)}, 400)

        group_id = request.json.get('group_id')
        if group_id is not None:
            user_partition_id = request.json.get('user_partition_id')
            if user_partition_id is None:
                # Note: error message not translated because it is not exposed to the user (UI prevents this state).
                return JsonResponse(
                    {"error": "If group_id is specified, user_partition_id must also be specified."}, 400
                )
            existing_group_id, existing_partition_id = cohorts.get_group_info_for_cohort(cohort)
            if group_id != existing_group_id or user_partition_id != existing_partition_id:
                unlink_cohort_partition_group(cohort)
                link_cohort_to_partition_group(cohort, user_partition_id, group_id)
        else:
            # If group_id was specified as None, unlink the cohort if it previously was associated with a group.
            existing_group_id, _ = cohorts.get_group_info_for_cohort(cohort)
            if existing_group_id is not None:
                unlink_cohort_partition_group(cohort)

        return JsonResponse(_get_cohort_representation(cohort, course))


@ensure_csrf_cookie
def users_in_cohort(request, course_key_string, cohort_id):
    """
    Return users in the cohort.  Show up to 100 per page, and page
    using the 'page' GET attribute in the call.  Format:

    Returns:
        Json dump of dictionary in the following format:
        {'success': True,
         'page': page,
         'num_pages': paginator.num_pages,
         'users': [{'username': ..., 'email': ..., 'name': ...}]
    }
    """
    # this is a string when we get it here
    course_key = CourseKey.from_string(course_key_string)

    get_course_with_access(request.user, 'staff', course_key)

    # this will error if called with a non-int cohort_id.  That's ok--it
    # shouldn't happen for valid clients.
    cohort = cohorts.get_cohort_by_id(course_key, int(cohort_id))

    paginator = Paginator(cohort.users.all(), 100)
    try:
        page = int(request.GET.get('page'))
    except (TypeError, ValueError):
        # These strings aren't user-facing so don't translate them
        return HttpResponseBadRequest('Requested page must be numeric')
    else:
        if page < 0:
            return HttpResponseBadRequest('Requested page must be greater than zero')

    try:
        users = paginator.page(page)
    except EmptyPage:
        users = []  # When page > number of pages, return a blank page

    user_info = [{'username': u.username,
                  'email': u.email,
                  'name': '{0} {1}'.format(u.first_name, u.last_name)}
                 for u in users]

    return json_http_response({'success': True,
                               'page': page,
                               'num_pages': paginator.num_pages,
                               'users': user_info})


@ensure_csrf_cookie
@require_POST
def add_users_to_cohort(request, course_key_string, cohort_id):
    """
    Return json dict of:

    {'success': True,
     'added': [{'username': ...,
                'name': ...,
                'email': ...}, ...],
     'changed': [{'username': ...,
                  'name': ...,
                  'email': ...,
                  'previous_cohort': ...}, ...],
     'present': [str1, str2, ...],    # already there
     'unknown': [str1, str2, ...],
     'preassigned': [str1, str2, ...],
     'invalid': [str1, str2, ...]}

     Raises Http404 if the cohort cannot be found for the given course.
    """
    # this is a string when we get it here
    course_key = CourseKey.from_string(course_key_string)
    get_course_with_access(request.user, 'staff', course_key)

    try:
        cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
    except CourseUserGroup.DoesNotExist:
        raise Http404("Cohort (ID {cohort_id}) not found for {course_key_string}".format(
            cohort_id=cohort_id,
            course_key_string=course_key_string
        ))

    users = request.POST.get('users', '')
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

    return json_http_response({'success': True,
                               'added': added,
                               'changed': changed,
                               'present': present,
                               'unknown': unknown,
                               'preassigned': preassigned,
                               'invalid': invalid})


@ensure_csrf_cookie
@require_POST
def remove_user_from_cohort(request, course_key_string, cohort_id):
    """
    Expects 'username': username in POST data.

    Return json dict of:

    {'success': True} or
    {'success': False,
     'msg': error_msg}
    """
    # this is a string when we get it here
    course_key = CourseKey.from_string(course_key_string)
    get_course_with_access(request.user, 'staff', course_key)

    username = request.POST.get('username')
    if username is None:
        return json_http_response({'success': False, 'msg': 'No username specified'})

    try:
        api.remove_user_from_cohort(course_key, username)
    except User.DoesNotExist:
        log.debug('no user')
        return json_http_response({'success': False, 'msg': "No user '{0}'".format(username)})
    except CohortMembership.DoesNotExist:
        pass

    return json_http_response({'success': True})


def debug_cohort_mgmt(request, course_key_string):
    """
    Debugging view for dev.
    """
    # this is a string when we get it here
    course_key = CourseKey.from_string(course_key_string)
    # add staff check to make sure it's safe if it's accidentally deployed.
    get_course_with_access(request.user, 'staff', course_key)

    context = {'cohorts_url': reverse(
        'cohorts',
        kwargs={'course_key': text_type(course_key)}
    )}
    return render_to_response('/course_groups/debug.html', context)


class APIPermissions(APIView):
    authentication_classes = (JwtAuthentication, OAuth2Authentication, SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser)


class CohortSettings(DeveloperErrorViewMixin, APIPermissions):
    """
    Endpoints for dealing with cohort settings for a course.
    """

    def get(self, request, course_key_string):
        """
        Endpoint to fetch the course cohort settings.
        """
        course_key, _ = api.get_course(request, course_key_string)
        return Response(_cohort_settings(course_key))

    def put(self, request, course_key_string):
        """
        Endpoint to set the course cohort settings.
        """
        course_key, _ = api.get_course(request, course_key_string)

        if 'is_cohorted' not in request.data:
            raise self.api_error(status.HTTP_400_BAD_REQUEST,
                                 'Missing field "is_cohorted".')
        try:
            cohorts.set_course_cohorted(course_key, request.data.get('is_cohorted'))
        except ValueError as err:
            raise self.api_error(status.HTTP_400_BAD_REQUEST, err)
        return Response(_cohort_settings(course_key))


class CohortHandler(DeveloperErrorViewMixin, APIPermissions):
    """
    Endpoints dealing directly with the cohorts.
    """

    def get(self, request, course_key_string, cohort_id=None):
        """
        Endpoint to get either one or all cohorts.
        """
        course_key, course = api.get_course(request, course_key_string)
        if not cohort_id:
            response = {'cohorts': [
                _get_cohort_representation(c, course)
                for c in cohorts.get_course_cohorts(course)
            ]}
            return Response(response)
        else:
            cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
            return Response(_get_cohort_representation(cohort, course))

    def post(self, request, course_key_string, cohort_id=None):
        """
        Endpoint to create a new cohort, must not include cohort_id.
        """
        assert cohort_id is None
        course_key, course = api.get_course(request, course_key_string)
        name = request.data.get('name')
        if not name:
            raise self.api_error(status.HTTP_400_BAD_REQUEST,
                                 'Cohort name must be specified.',
                                 'missing-cohort-name')
        assignment_type = request.data.get('assignment_type')
        if not assignment_type:
            raise self.api_error(status.HTTP_400_BAD_REQUEST,
                                 'Assignment type must be specified.',
                                 'missing-assignment-type')
        return Response(_get_cohort_representation(cohorts.add_cohort(course_key, name, assignment_type), course))

    def patch(self, request, course_key_string, cohort_id=None):
        """
        Endpoint to update a cohort information, including:
            + name
            + group_id
            + user_partition_id
        """
        assert cohort_id is not None
        course_key, _ = api.get_course(request, course_key_string)
        cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
        name = request.data.get('name')
        assert name is not None
        if name != cohort.name:
            if cohorts.is_cohort_exists(course_key, name):
                raise self.api_error(status.HTTP_400_BAD_REQUEST,
                                     'A cohort with the same name already exists.',
                                     'cohort-name-exists')
            cohort.name = name
            cohort.save()
        assignment_type = request.data.get('assignment_type')
        assert assignment_type is not None
        cohorts.set_assignment_type(cohort, assignment_type)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CohortUsers(DeveloperErrorViewMixin, APIPermissions):
    """
    Endpoints dealing directly with users in the cohorts.
    """

    # pylint: disable=unused-argument
    def delete(self, request, course_key_string, cohort_id, username=None):
        """
        Removes and user from a specific cohort.

        Note: It's better to use the post method to move users between cohorts.
        """
        course_key, _ = api.get_course(request, course_key_string)
        try:
            api.remove_user_from_cohort(course_key, username)
        except User.DoesNotExist:
            raise self.api_error(status.HTTP_404_NOT_FOUND, 'User does not exist.', 'user-not-found')
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, course_key_string, cohort_id, username=None):
        """
        Add given users to the cohort.
        """
        assert username is None
        course_key, _ = api.get_course(request, course_key_string)
        try:
            cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
        except CourseUserGroup.DoesNotExist:
            msg = 'Cohort (ID {cohort_id}) not found for {course_key_string}'.format(
                cohort_id=cohort_id,
                course_key_string=course_key_string
            )
            raise self.api_error(status.HTTP_404_NOT_FOUND, msg, 'cohort-not-found')

        added, changed, present, unknown, preassigned, invalid = [], [], [], [], [], []
        for username_or_email in request.data.get('users', []):
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

        return Response({'success': True,
                         'added': added,
                         'changed': changed,
                         'present': present,
                         'unknown': unknown,
                         'preassigned': preassigned,
                         'invalid': invalid})


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class CohortCSV(DeveloperErrorViewMixin, APIPermissions):
    """
    Endpoint for adding users via CSV file
    """

    def post(self, request, course_key_string):
        """
            View method that accepts an uploaded file (using key "uploaded-file")
            containing cohort assignments for users. This method spawns a celery task
            to do the assignments, and a CSV file with results is provided via data downloads.
            """
        course_key, _ = api.get_course(request, course_key_string)
        try:
            __, file_name = store_uploaded_file(
                request, 'uploaded-file', ['.csv'],
                course_and_time_based_filename_generator(course_key, 'cohorts'),
                max_file_size=2000000,  # limit to 2 MB
                validator=api.csv_validator
            )

            submit_task(request, 'cohort_students', cohort_students, course_key, {'file_name': file_name}, "")
        except (FileValidationException, ValueError) as e:
            raise self.api_error(status.HTTP_400_BAD_REQUEST, str(e), 'failed-validation')
        return Response(status=status.HTTP_204_NO_CONTENT)
