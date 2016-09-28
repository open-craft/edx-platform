"""
The Enrollment API Views should be simple, lean HTTP endpoints for API access. This should
consist primarily of authentication, request validation, and serialization.

"""
import json
import logging

from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.course_groups.cohorts import is_course_cohorted
from openedx.core.lib.api.authentication import (
    OAuth2AuthenticationAllowInactiveUser,
)
from openedx.core.lib.api.permissions import ApiKeyHeaderPermissionIsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

import instructor_analytics.basic
import instructor_analytics.csvs
import instructor_analytics.distributions
from courseware.courses import get_course_by_id
from enrollment.views import EnrollmentUserThrottle, ApiKeyPermissionMixIn, EnrollmentCrossDomainSessionAuth
from instructor.views.api import students_update_enrollment, require_level
from instructor_task.api_helper import AlreadyRunningError
from microsite_configuration import microsite
from util.disable_rate_limit import can_disable_rate_limit
from util.json_request import JsonResponse
from .serializers import BulkEnrollmentSerializer
from appsembler.enrollment.api import submit_calculate_students_features_csv

log = logging.getLogger(__name__)


@can_disable_rate_limit
class BulkEnrollView(APIView, ApiKeyPermissionMixIn):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, EnrollmentCrossDomainSessionAuth
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    def post(self, request):
        serializer = BulkEnrollmentSerializer(data=request.data)
        if serializer.is_valid():
            request.POST = request.data
            response_dict = {
                'auto_enroll': serializer.data.get('auto_enroll'),
                'email_students': serializer.data.get('email_students'),
                'action': serializer.data.get('action'),
                'courses': {}
            }
            for course in serializer.data.get('courses'):
                response = students_update_enrollment(self.request, course_id=course)
                response_dict['courses'][course] = json.loads(response.content)
            return Response(data=response_dict, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

bulk_enroll_view = BulkEnrollView.as_view()

@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_students_features(request, course_id, csv=False):  # pylint: disable=redefined-outer-name
    """
    Respond with json which contains a summary of all enrolled students profile information.

    Responds with JSON
        {"students": [{-student-info-}, ...]}

    TO DO accept requests for different attribute sets.
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_by_id(course_key)

    available_features = instructor_analytics.basic.AVAILABLE_FEATURES

    # Allow for microsites to be able to define additional columns (e.g. )
    query_features = microsite.get_value('student_profile_download_fields')

    if not query_features:
        query_features = [
            'id', 'username', 'name', 'email', 'language', 'location',
            'year_of_birth', 'gender', 'level_of_education', 'mailing_address',
            'goals', 'is_active'
        ]

    # Provide human-friendly and translatable names for these features. These names
    # will be displayed in the table generated in data_download.coffee. It is not (yet)
    # used as the header row in the CSV, but could be in the future.
    query_features_names = {
        'id': _('User ID'),
        'username': _('Username'),
        'name': _('Name'),
        'email': _('Email'),
        'language': _('Language'),
        'location': _('Location'),
        'year_of_birth': _('Birth Year'),
        'gender': _('Gender'),
        'level_of_education': _('Level of Education'),
        'mailing_address': _('Mailing Address'),
        'goals': _('Goals'),
        'is_active': _('Is Active')
    }

    if is_course_cohorted(course.id):
        # Translators: 'Cohort' refers to a group of students within a course.
        query_features.append('cohort')
        query_features_names['cohort'] = _('Cohort')

    if not csv:
        student_data = instructor_analytics.basic.enrolled_students_features(course_key, query_features)
        response_payload = {
            'course_id': unicode(course_key),
            'students': student_data,
            'students_count': len(student_data),
            'queried_features': query_features,
            'feature_names': query_features_names,
            'available_features': available_features,
        }
        return JsonResponse(response_payload)
    else:
        try:
            submit_calculate_students_features_csv(request, course_key, query_features)
            success_status = _("Your enrolled student profile report is being generated! You can view the status of the generation task in the 'Pending Instructor Tasks' section.")
            return JsonResponse({"status": success_status})
        except AlreadyRunningError:
            already_running_status = _("An enrolled student profile report generation task is already in progress. Check the 'Pending Instructor Tasks' table for the status of the task. When completed, the report will be available for download in the table below.")
            return JsonResponse({"status": already_running_status})
