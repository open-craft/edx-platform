"""
This file contains tasks for asynchronous execution of additional grade reports.
"""

from celery import task
from celery.result import AsyncResult

from lms.djangoapps.grades_report.grade_services import GradeServices


@task(bind=True)
def calculate_grades_report(self, course_id, submit_report_type):
    """
    Returns the result of the requested type report,
    or dict with an error key
    """
    if course_id is not None:
        return GradeServices().generate(course_id, submit_report_type)
    else:
        return {'error': 'No course_id data provided'}


def get_task_result_by_id(task_id):
    task_result = AsyncResult(task_id)
    return task_result
