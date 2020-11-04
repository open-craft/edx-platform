"""Module containing a task for user progress migration"""

import csv
import logging

from io import BytesIO

from celery.task import task
from completion.models import BlockCompletion
from courseware.courses import get_course
from courseware.models import StudentModule
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail.message import EmailMessage
from django.db import transaction
from django.utils.translation import ugettext as _
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from student.models import AnonymousUserId, anonymous_id_for_user, CourseEnrollment
from submissions.models import StudentItem

log = logging.getLogger(__name__)

OUTCOME_SOURCE_NOT_FOUND = 'source email not found'
OUTCOME_SOURCE_NOT_ENROLLED = 'source email not enrolled in given course'
OUTCOME_TARGET_NOT_FOUND = 'target email not found'
OUTCOME_TARGET_ALREADY_ENROLLED = 'target email already enrolled in given course'
OUTCOME_COURSE_KEY_INVALID = 'course key invalid'
OUTCOME_COURSE_NOT_FOUND = 'course key not found'
OUTCOME_FAILED_MIGRATION = 'failed to migrate progress'
OUTCOME_MIGRATED = 'migrated'


@task(bind=True)
def migrate_progress(self, migrate_list, result_recipients=None):
    """
    Task that migrates progress from one user to another
    """

    log.info('Started progress migration. Items to process: %s', len(migrate_list))

    # Starting migrating completions for each entry
    results = [{
        'course': course,
        'source_email': source,
        'dest_email': target,
        'outcome': _migrate_progress(course, source, target)
    } for (course, source, target) in migrate_list]

    results_csv = _create_results_csv(results)
    _send_email_with_results(result_recipients, results_csv)


def _create_results_csv(results):
    """
    Turns results of migration into csv bytestring.
    """

    fieldnames = ['course', 'source_email', 'dest_email', 'outcome']

    csv_file = BytesIO()

    writer = csv.DictWriter(csv_file, fieldnames)
    writer.writeheader()
    writer.writerows(results)

    return csv_file.getvalue()


def _send_email_with_results(recepients, results_csv):
    """
    Triggers email with csv attachment.
    """

    email_subject = _('Progress migration result')
    email_text = _('Migration is finished. Please review this email attachment.')

    from_address = configuration_helpers.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
    recepients = recepients or [settings.SERVER_EMAIL]
    attachment_name = 'MigrationResults.csv'

    email = EmailMessage()
    email.subject = email_subject
    email.body = email_text
    email.from_email = from_address
    email.to = recepients
    email.attach(attachment_name, results_csv, 'text/csv')

    email.send()

    log.info('Email with users progress migration results sent to %s', recepients)


def _migrate_progress(course, source, target):
    """
    Task that migrates progress from one user to another
    """
    log.info('Started progress migration from "%s" to "%s" for "%s" course', source, target, course)

    try:
        course_key = CourseKey.from_string(course)
    except InvalidKeyError:
        log.warning('Migration failed. Invalid course key: %s', course)
        return OUTCOME_COURSE_KEY_INVALID

    try:
        get_course(course_key)
    except ValueError:
        log.warning('Migration failed. Course not found:: %s', course_key)
        return OUTCOME_COURSE_NOT_FOUND

    try:
        source = get_user_model().objects.get(email=source)
    except ObjectDoesNotExist:
        log.warning('Migration failed. Source user with such email not found: %s', source)
        return OUTCOME_SOURCE_NOT_FOUND

    try:
        enrollment = CourseEnrollment.objects.select_for_update().get(user=source, course=course_key)
    except ObjectDoesNotExist:
        log.warning(
            'Migration failed. Source user with email "%s" not enrolled in "%s" course', source.email, course_key
        )
        return OUTCOME_SOURCE_NOT_ENROLLED

    try:
        target = get_user_model().objects.get(email=target)
    except ObjectDoesNotExist:
        log.warning('Migration failed. Target user with such email not found: %s', target)
        return OUTCOME_TARGET_NOT_FOUND

    if CourseEnrollment.objects.filter(user=target, course=course_key).exists():
        log.warning(
            'Migration failed. Target user with email "%s" already enrolled in "%s" course', target.email, course_key
        )
        return OUTCOME_TARGET_ALREADY_ENROLLED

    # Fetch completions for source user
    completions = BlockCompletion.user_course_completion_queryset(
        user=source, course_key=course_key
    ).select_for_update()

    # Fetch edx-submissions data for source user
    anonymous_ids = AnonymousUserId.objects.filter(user=source, course_id=course_key).values('anonymous_user_id')
    submissions = StudentItem.objects.select_for_update().filter(course_id=course_key, student_id__in=anonymous_ids)

    # Fetch StudentModule table data for source user
    student_states = StudentModule.objects.select_for_update().filter(student=source, course_id=course_key)

    # Actually migrate completions and progress
    try:
        with transaction.atomic():
            # Modify enrollment
            enrollment.user = target
            enrollment.save()

            # Migrate completions for user
            for completion in completions:
                completion.user = target
                completion.save()

            # Migrate edx-submissions
            for submission in submissions:
                submission.student_id = anonymous_id_for_user(target, course_key)
                submission.save()

            # Migrate StudentModule
            for state in student_states:
                state.student = target
                state.save()

    except Exception:
        log.exception("Unexpected error while migrating user progress.")
        return OUTCOME_FAILED_MIGRATION

    log.info(
        'User progress in "%s" course successfully migrated from "%s" to "%s"', course_key, source.email, target.email
    )
    return OUTCOME_MIGRATED
