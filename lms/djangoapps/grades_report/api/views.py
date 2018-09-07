""" API views. """
from __future__ import absolute_import, unicode_literals

from celery.exceptions import TimeoutError
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from lms.djangoapps.grades_report.tasks import (
    get_task_result_by_id,
    calculate_by_section_grades_report,
    calculate_enhanced_problem_grades_report,
)
from openedx.core.lib.api.view_utils import view_auth_classes


@view_auth_classes()
class BySectionGradeReportView(GenericAPIView):
    """
    **Use Case**

        Get the additional by section grade report.

    **Example requests**:

        * Report by section
        GET api/grades_report/{course_id}/report_by_section/

        * Report by section, with up-to-date-grade of the block_id requested
        GET api/grades_report/{course_id}/report_by_section/{block_id}/

    **Response Values**

        * status: Message status of the report request.

        * url: The absolute url to json resource.
    """
    def get(self, request, course_id, **kwargs):
        """
        Public method to send a Celery task, and then, generate a JSON object representation
        with status and url of the by section grade report requested.
        """
        section_block_id = ''
        if 'usage_key_string' in kwargs:
            section_block_id = kwargs['usage_key_string']

        grades_report_task = calculate_by_section_grades_report.apply_async(args=(course_id, section_block_id))
        resource_url = generate_reverse_url(grades_report_task.task_id)
        success_status = _("The by section grade report is being created.")
        return Response({
            'status': success_status,
            'url': resource_url,
        }, status=status.HTTP_200_OK)


@view_auth_classes()
class ByAssignmentTypeGradeReportView(GenericAPIView):
    """
    **Use Case**

        Get the additional by assignment type grade report.

    **Example requests**:

        * Report by assignment type
        GET api/grades_report/{course_id}/report_by_assignment_type/

        * Report by assignment type, with up-to-date-grade of the block_id requested
        GET api/grades_report/{course_id}/report_by_assignment_type/{block_id}/

    **Response Values**

        * status: Message status of the report request.

        * url: The absolute url to json resource.
    """
    def get(self, request, course_id, **kwargs):
        """
        Public method to send a Celery task, and then, generate a JSON object representation
        with status and url of the by assignment type report requested.
        """
        section_block_id = ''
        if 'usage_key_string' in kwargs:
            section_block_id = kwargs['usage_key_string']

        grades_report_task = calculate_by_section_grades_report.apply_async(args=(course_id, section_block_id))
        resource_url = generate_reverse_url(grades_report_task.task_id)
        success_status = _("The by assignment type report is being created.")
        return Response({
            'status': success_status,
            'url': resource_url,
        }, status=status.HTTP_200_OK)


@view_auth_classes()
class EnhancedProblemGradeReportView(GenericAPIView):
    """
    **Use Case**

        Get the additional enhanced problem grade report.

    **Example requests**:

        * Enhanced problem grade report
        GET api/grades_report/{course_id}/report_enhanced_problem_grade/

    **Response Values**

        * status: Message status of the report request.

        * url: The absolute url to json resource.
    """
    def get(self, request, course_id):
        """
        Public method to send a Celery task, and then, generate a JSON object representation
        with status and url of the enhanced problem report requested.
        """
        grades_report_task = calculate_enhanced_problem_grades_report.apply_async(args=[course_id])
        resource_url = generate_reverse_url(grades_report_task.task_id)
        success_status = _("The enhanced problem report is being created.")
        return Response({
            'status': success_status,
            'url': resource_url,
        }, status=status.HTTP_200_OK)


@view_auth_classes()
class GradeReportByTaskId(GenericAPIView):
    """
    **Use Case**

        Get the json resource with the report by section data according to task uuid.

    **Example requests**:

        GET api/grades_report/report/{uuid}/

    **Response Values**

        * data: Json object representation with the additional report data.

    """
    def get(self, request, uuid, **kwargs): # pylint: disable=W0613
        """
        Public get method to obtain the json object with the result
        of the grade report, by task id.
        """
        try:
            task_output = get_task_result_by_id(uuid)
        except TimeoutError:
            return Response({
                'error': 'There was a TimeOutError getting the task_output.'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        else:
            if task_output.ready():
                if task_output.failed():
                    return Response({'error': str(task_output.result)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response({'data': task_output.result}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'Task output is not ready yet.'}, status=status.HTTP_202_ACCEPTED)


def generate_reverse_url(task_id):
    """
    Util function to generate reverse url to get the final report by task_id.
    """
    url_from_reverse = reverse('grades_report_api:grade_course_report_generated', args=[task_id])
    host_url = getattr(settings, 'LMS_ROOT_URL', '')
    resource_url = '{}{}'.format(host_url, url_from_reverse)
    return resource_url
