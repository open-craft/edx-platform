"""
This file contains tasks for asynchronous execution of additional grade reports.
"""

from celery import task
from celery.result import AsyncResult

from lms.djangoapps.grades_report.grade_services import (
    BySectionGradeServices,
    ByAssignmentTypeGradeServices,
    EnhancedProblemGradeServices,
)


@task()
def calculate_by_section_grades_report(course_id, section_block_id=None):
    """
    Returns the result of the by section grade report.
    """
    return BySectionGradeServices(course_id).by_section(section_block_id)


@task()
def calculate_by_assignment_type_report(course_id, section_block_id=None):
    """
    Returns the result of the by section grade report.
    """
    return ByAssignmentTypeGradeServices(course_id).by_assignment_type(section_block_id)


@task()
def calculate_enhanced_problem_grades_report(course_id,):
    """
    Returns the result of the enhanced problem grade report.
    """
    return EnhancedProblemGradeServices(course_id).enhanced_problem_grade()


def get_task_result_by_id(task_id):
    """
    Returns the result of the task according to an provided uuid.
    """
    task_result = AsyncResult(task_id)
    return task_result
