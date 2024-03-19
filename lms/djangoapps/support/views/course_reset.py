""" Views for the course reset feature """

from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


from common.djangoapps.student.models import CourseEnrollment, get_user_by_username_or_email
from common.djangoapps.student.helpers import user_has_passing_grade_in_course
from lms.djangoapps.support.decorators import require_support_permission
from lms.djangoapps.support.models import (
    CourseResetCourseOptIn,
    CourseResetAudit
)

User = get_user_model()


def can_enrollment_be_reset(course_enrollment):
    """
    Args: enrollment (CourseEnrollment)
    Returns: tuple (boolean, string)
        [0]: whether or not the course can be reset
        [1]: a status message to present to the learner
             or None if there is nothing notable about the enrollment and it can be reset
    """
    course_overview = course_enrollment.course_overview
    if not course_overview.has_started():
        return False, "Course Not Started"
    if course_overview.has_ended():
        return False, "Course Ended"
    if user_has_passing_grade_in_course(course_enrollment):
        return False, "Learner Has Passing Grade"

    try:
        audit = course_enrollment.courseresetaudit_set.latest('modified')
    except CourseResetAudit.DoesNotExist:
        return True, None

    audit_status_message = audit.status_message()
    if audit.status == CourseResetAudit.CourseResetStatus.FAILED:
        return True, audit_status_message
    return False, audit_status_message


class CourseResetAPIView(APIView):
    """
    A view to handle requests related to the course reset feature.
    GET: List applicable courses, their statuses, and if they can be reset
    POST: Reset a course for the given learner
    """

    permission_classes = (
        IsAuthenticated,
    )

    @method_decorator(require_support_permission)
    def get(self, request, username_or_email):
        """
        List the enrollments for this user that are in courses that have opted into the
        course reset feature, including information about past resets or resets in progress, and
        whether or not the reset will be allowed to be done for each returned enrollment

        returns a list of dicts with the format [
            {
                'course_id': <course id>
                'display_name': <course display name>
                'status': <status of the enrollment wrt/reset, to be displayed to user>
                'can_reset': (boolean) <can the course be reset for this learner>
            }
        ]
        """
        try:
            user = get_user_by_username_or_email(username_or_email)
        except User.DoesNotExist:
            return Response([])
        all_enabled_resettable_course_ids = CourseResetCourseOptIn.all_active_course_ids()
        course_enrollments = CourseEnrollment.objects.filter(
            is_active=True,
            user=user,
            course__id__in=all_enabled_resettable_course_ids
        ).select_related("course").prefetch_related("courseresetaudit_set")

        result = []
        for course_enrollment in course_enrollments:
            course_overview = course_enrollment.course_overview
            can_reset, status_message = can_enrollment_be_reset(course_enrollment)
            result.append({
                'course_id': str(course_overview.id),
                'display_name': course_overview.display_name,
                'can_reset': can_reset,
                'status': status_message if status_message else "Available"
            })
        return Response(result)

    @method_decorator(require_support_permission)
    def post(self, request, username_or_email):
        """
        Resets a course for the given learner

        returns a dicts with the format {
            'course_id': <course id>
            'display_name': <course display name>
            'status': <status of the enrollment wrt/reset, to be displayed to user>
            'can_reset': (boolean) <can the course be reset for this learner>
        }
        """
        course_id = request.data['course_id']
        try:
            user = get_user_by_username_or_email(username_or_email)
        except User.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=404)
        try:
            opt_in_course = CourseResetCourseOptIn.objects.get(course_id=course_id)
        except CourseResetCourseOptIn.DoesNotExist:
            return Response({'error': 'Course is not eligible'}, status=404)
        enrollment = CourseEnrollment.objects.get(
            course=course_id,
            user=user,
            is_active=True
        )
        user_passed = user_has_passing_grade_in_course(enrollment=enrollment)
        course_overview = enrollment.course_overview
        course_reset_audit = CourseResetAudit.objects.filter(course_enrollment=enrollment).first()

        if course_reset_audit and (
            course_reset_audit.status == CourseResetAudit.CourseResetStatus.FAILED
            and not user_passed
        ):
            course_reset_audit.status = CourseResetAudit.CourseResetStatus.ENQUEUED
            course_reset_audit.save()
            # Call celery task
            resp = {
                'course_id': course_id,
                'status': course_reset_audit.status_message(),
                'can_reset': False,
                'display_name': course_overview.display_name
            }
            return Response(resp, status=200)

        elif course_reset_audit and course_reset_audit.status in (
            CourseResetAudit.CourseResetStatus.IN_PROGRESS,
            CourseResetAudit.CourseResetStatus.ENQUEUED
        ):
            return Response(None, status=204)

        if enrollment and opt_in_course and not user_passed:
            course_reset_audit = CourseResetAudit.objects.create(
                course=opt_in_course,
                course_enrollment=enrollment,
                reset_by=request.user,
            )
            resp = {
                'course_id': course_id,
                'status': course_reset_audit.status_message(),
                'can_reset': False,
                'display_name': course_overview.display_name
            }

            # Call celery task
            return Response(resp, status=201)
        else:
            return Response(None, status=400)
