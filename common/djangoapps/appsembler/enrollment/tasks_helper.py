import json
from datetime import datetime
from time import time

from django.contrib.auth.models import User
from pytz import UTC

from instructor_analytics.basic import STUDENT_FEATURES, PROFILE_FEATURES
from instructor_analytics.csvs import format_dictlist

from instructor_task.tasks_helper import upload_csv_to_report_store, TaskProgress
from student.models import CourseEnrollment



def upload_students_csv(_xmodule_instance_args, _entry_id, course_id, task_input, action_name):
    """
    For a given `course_id`, generate a CSV file containing profile
    information for all students that are enrolled, and store using a
    `ReportStore`.
    """
    start_time = time()
    start_date = datetime.now(UTC)
    enrolled_students = CourseEnrollment.objects.enrolled_and_dropped_out_users(course_id)
    task_progress = TaskProgress(action_name, enrolled_students.count(), start_time)

    current_step = {'step': 'Calculating Profile Info'}
    task_progress.update_task_state(extra_meta=current_step)

    # compute the student features table and format it
    query_features = task_input.get('features')
    student_data = enrolled_students_features(course_id, query_features)
    header, rows = format_dictlist(student_data, query_features)

    task_progress.attempted = task_progress.succeeded = len(rows)
    task_progress.skipped = task_progress.total - task_progress.attempted

    rows.insert(0, header)

    current_step = {'step': 'Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    # Perform the upload
    upload_csv_to_report_store(rows, 'student_profile_info', course_id, start_date)

    return task_progress.update_task_state(extra_meta=current_step)


def enrolled_students_features(course_key, features):
    """
    Return list of student features as dictionaries.

    enrolled_students_features(course_key, ['username', 'first_name'])
    would return [
        {'username': 'username1', 'first_name': 'firstname1'}
        {'username': 'username2', 'first_name': 'firstname2'}
        {'username': 'username3', 'first_name': 'firstname3'}
    ]
    """
    include_cohort_column = 'cohort' in features

    students = User.objects.filter(
        courseenrollment__course_id=course_key,
    ).order_by('username').select_related('profile')

    if include_cohort_column:
        students = students.prefetch_related('course_groups')

    def extract_student(student, features):
        """ convert student to dictionary """
        student_features = [x for x in STUDENT_FEATURES if x in features]
        profile_features = [x for x in PROFILE_FEATURES if x in features]

        # For data extractions on the 'meta' field
        # the feature name should be in the format of 'meta.foo' where
        # 'foo' is the keyname in the meta dictionary
        meta_features = []
        for feature in features:
            if 'meta.' in feature:
                meta_key = feature.split('.')[1]
                meta_features.append((feature, meta_key))

        student_dict = dict((feature, getattr(student, feature))
                            for feature in student_features)
        profile = student.profile
        if profile is not None:
            profile_dict = dict((feature, getattr(profile, feature))
                                for feature in profile_features)
            student_dict.update(profile_dict)

            # now featch the requested meta fields
            meta_dict = json.loads(profile.meta) if profile.meta else {}
            for meta_feature, meta_key in meta_features:
                student_dict[meta_feature] = meta_dict.get(meta_key)

        # check if users are currently enrolled in a course
        enrollment = CourseEnrollment.get_enrollment(student, course_key)
        if enrollment and enrollment.is_active:
            student_dict['is_active'] = True
        else:
            student_dict['is_active'] = False

        if include_cohort_column:
            # Note that we use student.course_groups.all() here instead of
            # student.course_groups.filter(). The latter creates a fresh query,
            # therefore negating the performance gain from prefetch_related().
            student_dict['cohort'] = next(
                (cohort.name for cohort in student.course_groups.all() if cohort.course_id == course_key),
                "[unassigned]"
            )
        return student_dict

    return [extract_student(student, features) for student in students]
