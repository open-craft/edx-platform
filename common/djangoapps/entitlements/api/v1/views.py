import logging

from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from edx_rest_framework_extensions.authentication import JwtAuthentication
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import permissions, viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from entitlements.api.v1.filters import CourseEntitlementFilter
from entitlements.api.v1.permissions import IsAdminOrAuthenticatedReadOnly
from entitlements.api.v1.serializers import CourseEntitlementSerializer
from entitlements.models import CourseEntitlement
from openedx.core.djangoapps.catalog.utils import get_course_runs_for_course
from openedx.core.djangoapps.cors_csrf.authentication import SessionAuthenticationCrossDomainCsrf
from student.models import CourseEnrollment
from student.models import CourseEnrollmentException, AlreadyEnrolledError

log = logging.getLogger(__name__)


class EntitlementViewSet(viewsets.ModelViewSet):
    ENTITLEMENT_UUID4_REGEX = '[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

    authentication_classes = (JwtAuthentication, SessionAuthenticationCrossDomainCsrf,)
    permission_classes = (permissions.IsAuthenticated, IsAdminOrAuthenticatedReadOnly,)
    lookup_value_regex = ENTITLEMENT_UUID4_REGEX
    lookup_field = 'uuid'
    serializer_class = CourseEntitlementSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = CourseEntitlementFilter

    def get_queryset(self):
        user = self.request.user

        if self.request.method in permissions.SAFE_METHODS:
            if (user.is_staff and
                    (self.request.query_params.get('user', None) is not None or
                     self.kwargs.get('uuid', None) is not None)):
                # Return the full query set so that the Filters class can be used to apply,
                # - The UUID Filter
                # - The User Filter to the GET request
                return CourseEntitlement.objects.all().select_related('user').select_related('enrollment_course_run')
            # Non Staff Users will only be able to retrieve their own entitlements
            return CourseEntitlement.objects.filter(user=user).select_related('user').select_related(
                'enrollment_course_run'
            )
        # All other methods require the full Query set and the Permissions class already restricts access to them
        # to Admin users
        return CourseEntitlement.objects.all().select_related('user').select_related('enrollment_course_run')

    def retrieve(self, request, *args, **kwargs):
        """
        Override the retrieve method to expire a record that is past the
        policy and is requested via the API before returning that record.
        """
        entitlement = self.get_object()
        entitlement.update_expired_at()
        serializer = self.get_serializer(entitlement)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        Override the list method to expire records that are past the
        policy and requested via the API before returning those records.
        """
        queryset = self.filter_queryset(self.get_queryset())
        user = self.request.user
        if not user.is_staff:
            with transaction.atomic():
                for entitlement in queryset:
                    entitlement.update_expired_at()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """
        This method is an override and is called by the DELETE method
        """
        save_model = False
        if instance.expired_at is None:
            instance.expired_at = timezone.now()
            log.info('Set expired_at to [%s] for course entitlement [%s]', instance.expired_at, instance.uuid)
            save_model = True

        if instance.enrollment_course_run is not None:
            CourseEnrollment.unenroll(
                user=instance.user,
                course_id=instance.enrollment_course_run.course_id,
                skip_refund=True
            )
            enrollment = instance.enrollment_course_run
            instance.enrollment_course_run = None
            save_model = True
            log.info(
                'Unenrolled user [%s] from course run [%s] as part of revocation of course entitlement [%s]',
                instance.user.username,
                enrollment.course_id,
                instance.uuid
            )
        if save_model:
            instance.save()


class EntitlementEnrollmentViewSet(viewsets.GenericViewSet):
    """
    Endpoint in the Entitlement API to handle the Enrollment of a User's Entitlement.
    This API will handle
        - Enroll
        - Unenroll
        - Switch Enrollment
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = CourseEntitlement.objects.all()

    def _verify_course_run_for_entitlement(self, entitlement, course_run_id):
        """
        Verifies that a Course run is a child of the Course assigned to the entitlement.
        """
        course_runs = get_course_runs_for_course(entitlement.course_uuid)
        for run in course_runs:
            if course_run_id == run.get('key', ''):
                return True
        return False

    def _enroll_entitlement(self, entitlement, course_run_key, user):
        """
        Internal method to handle the details of enrolling a User in a Course Run.

        Returns a response object is there is an error or exception, None otherwise
        """
        try:
            enrollment = CourseEnrollment.enroll(
                user=user,
                course_key=course_run_key,
                mode=entitlement.mode,
                check_access=True
            )
        except AlreadyEnrolledError:
            enrollment = CourseEnrollment.get_enrollment(user, course_run_key)
            if enrollment.mode == entitlement.mode:
                CourseEntitlement.set_enrollment(entitlement, enrollment)
            # Else the User is already enrolled in another Mode and we should
            # not do anything else related to Entitlements.
        except CourseEnrollmentException:
            message = (
                'Course Entitlement Enroll for {username} failed for course: {course_id}, '
                'mode: {mode}, and entitlement: {entitlement}'
            ).format(
                username=user.username,
                course_id=course_run_key,
                mode=entitlement.mode,
                entitlement=entitlement.uuid
            )
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'message': message}
            )

        CourseEntitlement.set_enrollment(entitlement, enrollment)
        return None

    def _unenroll_entitlement(self, entitlement, course_run_key, user):
        """
        Internal method to handle the details of Unenrolling a User in a Course Run.
        """
        CourseEnrollment.unenroll(user, course_run_key, skip_refund=True)
        CourseEntitlement.set_enrollment(entitlement, None)

    def create(self, request, uuid):
        """
        On POST this method will be called and will handle enrolling a user in the
        provided course_run_id from the data. This is called on a specific entitlement
        UUID so the course_run_id has to correspond to the Course that is assigned to
        the Entitlement.

        When this API is called for a user who is already enrolled in a run that User
        will be unenrolled from their current run and enrolled in the new run if it is
        available.
        """
        course_run_id = request.data.get('course_run_id', None)

        if not course_run_id:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data='The Course Run ID was not provided.'
            )

        # Verify that the user has an Entitlement for the provided Course UUID.
        try:
            entitlement = CourseEntitlement.objects.get(uuid=uuid, user=request.user, expired_at=None)
        except CourseEntitlement.DoesNotExist:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data='The Entitlement for this UUID does not exist or is Expired.'
            )

        # Verify the course run ID is of the same type as the Course entitlement.
        course_run_valid = self._verify_course_run_for_entitlement(entitlement, course_run_id)
        if not course_run_valid:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    'message': 'The Course Run ID is not a match for this Course Entitlement.'
                }
            )

        # Determine if this is a Switch session or a simple enroll and handle both.
        try:
            course_run_string = CourseKey.from_string(course_run_id)
        except InvalidKeyError:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    'message': 'Invalid {course_id}'.format(course_id=course_run_id)
                }
            )
        if entitlement.enrollment_course_run is None:
            response = self._enroll_entitlement(
                entitlement=entitlement,
                course_run_key=course_run_string,
                user=request.user
            )
            if response:
                return response
        elif entitlement.enrollment_course_run.course_id != course_run_id:
            self._unenroll_entitlement(
                entitlement=entitlement,
                course_run_key=entitlement.enrollment_course_run.course_id,
                user=request.user
            )
            response = self._enroll_entitlement(
                entitlement=entitlement,
                course_run_key=course_run_string,
                user=request.user
            )
            if response:
                return response

        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'course_run_id': course_run_id,
            }
        )

    def destroy(self, request, uuid):
        """
        On DELETE call to this API we will unenroll the course enrollment for the provided uuid
        """
        try:
            entitlement = CourseEntitlement.objects.get(uuid=uuid, user=request.user, expired_at=None)
        except CourseEntitlement.DoesNotExist:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data='The Entitlement for this UUID does not exist or is Expired.'
            )

        if entitlement.enrollment_course_run is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        self._unenroll_entitlement(
            entitlement=entitlement,
            course_run_key=entitlement.enrollment_course_run.course_id,
            user=request.user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
