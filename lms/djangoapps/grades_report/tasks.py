"""
This file contains tasks for asynchronous execution of additional grade reports.
"""

from celery import task
from celery.result import AsyncResult

from lms.djangoapps.grades_report.grade_services import (
    GradeServices,
    BySectionGradeServices,
)


@task()
def calculate_grades_report(course_id, submit_report_type):
    """
    Returns the result of the requested type report.
    """
    return GradeServices().generate(course_id, submit_report_type)


@task()
def calculate_by_section_grades_report(course_id, section_block_id=None):
    """
    Returns the result of the by section grade report.
    """
    return BySectionGradeServices(course_id).by_section(section_block_id)


def get_task_result_by_id(task_id):
    """
    Returns the result of the task according to an provided uuid.
    """
    task_result = AsyncResult(task_id)
    return task_result
