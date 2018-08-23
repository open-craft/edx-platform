""" Grades API URLs. """
from django.conf import settings
from django.conf.urls import patterns, url

from lms.djangoapps.grades.api import views

urlpatterns = patterns(
    '',
    url(
        r'^v0/course_grade/{course_id}/users/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.UserGradeView.as_view(), name='user_grade_detail'
    ),
    url(
        r'^v0/courses/{course_id}/policy/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.CourseGradingPolicy.as_view(), name='course_grading_policy'
    ),
    url(
        r'^v0/course_grade/{course_id}/report_by_section/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.AdditionalGradeReport.as_view(), name='grade_course_report_by_section'
    ),
    url(
        r'^v0/course_grade/{course_id}/report_by_section/{block_id}/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
            block_id=settings.USAGE_KEY_PATTERN,
        ),
        views.AdditionalGradeReport.as_view(), name='grade_course_report_by_section'
    ),
    url(
        r'^v0/course_grade/{course_id}/report_by_assignment_type/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.AdditionalGradeReport.as_view(), name='grade_course_report_by_assignment_type'
    ),
    url(
        r'^v0/course_grade/{course_id}/report_by_assignment_type/{block_id}/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
            block_id=settings.USAGE_KEY_PATTERN,
        ),
        views.AdditionalGradeReport.as_view(), name='grade_course_report_by_assignment_type'
    ),
    url(
        r'^v0/course_grade/{course_id}/report_enhanced_problem_grade/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.AdditionalGradeReport.as_view(), name='grade_course_report_enhanced_problem_grade'
    ),
    url(
        r'^v0/course_grade/report/(?P<uuid>[-\w]+)/$',
        views.GradeReportByTaskId.as_view(), name='grade_course_report_generated'
    ),
)
