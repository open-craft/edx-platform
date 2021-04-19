"""
Celery tasks used by periodic_instructor_reports
"""
import logging
from datetime import date

from celery import task
from django.contrib.auth.models import User
from django.http.request import HttpRequest

from opaque_keys.edx.locations import SlashSeparatedCourseKey
from instructor_task.api import submit_calculate_grades_csv, submit_calculate_students_features_csv

logger = logging.getLogger(__name__)

PERIODIC_REPORT_TASKS = {
    "calculate_grades_csv": submit_calculate_grades_csv,
    "calculate_students_features_csv": submit_calculate_students_features_csv,
}


@task # pylint: disable=not-callable
def periodic_task_wrapper(course_ids, *args, **kwargs):
    """
    Call instructor tasks in a periodic way. 
    """

    task_name = kwargs.get("task_name")
    report_task = PERIODIC_REPORT_TASKS.get(task_name)

    if not report_task:
        logger.error('Periodic report generation called for an unknow task: "%s"', task_name)
        return

    creator_email = kwargs.get("creator_email", "")
    creator = User.objects.filter(email=creator_email)

    if not creator.exists():
        logger.error('Periodic report creator email does not exsist: "%s"', creator_email)
        return 

    # Create a fake request object as it is needed for the instructor tasks
    request = HttpRequest()
    request.user = creator.last()

    # Assign metadata needed for parsing the request properly
    request.META = {
        "REMOTE_ADDR": "0.0.0.0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": 0,
    }

    use_folders_by_date = kwargs.get("use_folders_by_date", False)
    filename = kwargs.get("filename", None)

    for course_id in course_ids:
        task_kwargs = {}

        if filename:
            task_kwargs.update({
                "filename": filename
            })

        if use_folders_by_date:
            task_kwargs.update({
                "upload_parent_dir": date.today().strftime("%Y/%m/%d")
            })

        logger.info('Calling periodic "%s" for course "%s"', task_name, course_id)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        report_task(request, course_key, *args, **task_kwargs)
