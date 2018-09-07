""" Grade reports API URLs. """
from django.conf import settings
from django.conf.urls import patterns, url

from lms.djangoapps.grades_report.api import views

urlpatterns = patterns(
    '',
    url(
        r'^{course_id}/report_by_section/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.BySectionGradeReportView.as_view(), name='grade_course_report_by_section'
    ),
    url(
        r'^{course_id}/report_by_section/{block_id}/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
            block_id=settings.USAGE_KEY_PATTERN,
        ),
        views.BySectionGradeReportView.as_view(), name='grade_course_report_by_section_block_id'
    ),
    url(
        r'^{course_id}/report_by_assignment_type/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.ByAssignmentTypeGradeReportView.as_view(), name='grade_course_report_by_assignment_type'
    ),
    url(
        r'^{course_id}/report_by_assignment_type/{block_id}/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
            block_id=settings.USAGE_KEY_PATTERN,
        ),
        views.ByAssignmentTypeGradeReportView.as_view(), name='grade_course_report_by_assignment_type_block_id'
    ),
    url(
        r'^{course_id}/report_enhanced_problem_grade/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.EnhancedProblemGradeReportView.as_view(), name='grade_course_report_enhanced_problem_grade'
    ),
    url(
        r'^report/(?P<uuid>[-\w]+)/$',
        views.GradeReportByTaskId.as_view(), name='grade_course_report_generated'
    ),
)
