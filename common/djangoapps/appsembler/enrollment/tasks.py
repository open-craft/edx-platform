from functools import partial

from django.conf import settings
from django.utils.translation import ugettext_noop
from celery import task

from instructor_task.tasks_helper import BaseInstructorTask, run_main_task
from appsembler.enrollment.tasks_helper import upload_students_csv



@task(
    base=BaseInstructorTask,
    routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY
)  # pylint: disable=not-callable
def calculate_students_features_csv(entry_id, xmodule_instance_args):
    """
    Compute student profile information for a course and upload the
    CSV to an S3 bucket for download.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('generated')
    task_fn = partial(upload_students_csv, xmodule_instance_args)
    return run_main_task(entry_id, task_fn, action_name)




