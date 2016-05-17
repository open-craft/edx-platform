from appsembler.enrollment.tasks import calculate_students_features_csv
from instructor_task.api_helper import submit_task


def submit_calculate_students_features_csv(request, course_key, features):
    """
    Submits a task to generate a CSV containing student profile info.

    Raises AlreadyRunningError if said CSV is already being updated.
    """
    task_type = 'profile_info_csv'
    task_class = calculate_students_features_csv
    task_input = {'features': features}
    task_key = ""

    return submit_task(request, task_type, task_class, course_key, task_input, task_key)
