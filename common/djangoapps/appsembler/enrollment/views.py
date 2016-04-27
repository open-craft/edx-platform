"""
The Enrollment API Views should be simple, lean HTTP endpoints for API access. This should
consist primarily of authentication, request validation, and serialization.

"""
import json
import logging
from instructor.views.api import students_update_enrollment

from openedx.core.lib.api.permissions import ApiKeyHeaderPermissionIsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from openedx.core.lib.api.authentication import (
    OAuth2AuthenticationAllowInactiveUser,
)

from enrollment.views import EnrollmentUserThrottle, ApiKeyPermissionMixIn, EnrollmentCrossDomainSessionAuth
from util.disable_rate_limit import can_disable_rate_limit
from .serializers import BulkEnrollmentSerializer

log = logging.getLogger(__name__)


@can_disable_rate_limit
class BulkEnrollView(APIView, ApiKeyPermissionMixIn):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, EnrollmentCrossDomainSessionAuth
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    def post(self, request):
        serializer = BulkEnrollmentSerializer(data=request.DATA)
        if serializer.is_valid():
            request.POST = request.DATA
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
