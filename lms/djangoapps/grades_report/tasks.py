"""
This file contains tasks for asynchronous execution of additional grade reports.
"""

from celery import task
from celery.result import AsyncResult

from lms.djangoapps.grades_report.grade_services import GradeServices


@task()
def calculate_grades_report(course_id, submit_report_type):
    """
    Returns the result of the requested type report.
    """
    return GradeServices().generate(course_id, submit_report_type)


def get_task_result_by_id(task_id):
    """
    Returns the result of the task according to an provided uuid.
    """
    task_result = AsyncResult(task_id)
    return task_result
