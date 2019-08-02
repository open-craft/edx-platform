"""
Command to recalculate grades for all subsections with problem submissions
in the specified time range.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from pytz import utc

from courseware.models import StudentModule
from lms.djangoapps.grades.constants import ScoreDatabaseTableEnum
from lms.djangoapps.grades.events import PROBLEM_SUBMITTED_EVENT_TYPE
from lms.djangoapps.grades.tasks import recalculate_subsection_grade_v3
from openedx.core.lib.command_utils import parse_course_keys
from student.models import user_by_anonymous_id
from submissions.models import Submission
from track.event_transaction_utils import create_new_event_transaction_id, set_event_transaction_type
from util.date_utils import to_timestamp

log = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%d %H:%M"


class Command(BaseCommand):
    """
    Example usage:
        $ ./manage.py lms recalculate_subsection_grades
            --modified_start '2016-08-23 16:43' --modified_end '2016-08-25 16:43' --settings=devstack
    """
    args = 'fill this in'
    help = 'Recalculates subsection grades for all subsections modified within the given time range.'

    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        parser.add_argument(
            '--course',
            dest='course',
            nargs='+',
            help='ID of course that needs subsection grades computed.',
        )
        parser.add_argument(
            '--modified_start',
            dest='modified_start',
            help='Starting range for modified date (inclusive): e.g. "2016-08-23 16:43"; expected in UTC.',
        )
        parser.add_argument(
            '--modified_end',
            dest='modified_end',
            help='Ending range for modified date (inclusive): e.g. "2016-12-23 16:43"; expected in UTC.',
        )

    def handle(self, *args, **options):
        if 'modified_start' not in options:
            raise CommandError('modified_start must be provided.')

        if 'modified_end' not in options:
            raise CommandError('modified_end must be provided.')

        course_id = None
        if 'course' in options:
            course_ids = parse_course_keys(options['course'])
            course_id = course_ids[0] if course_ids else None

        modified_start = utc.localize(datetime.strptime(options['modified_start'], DATE_FORMAT))
        modified_end = utc.localize(datetime.strptime(options['modified_end'], DATE_FORMAT))
        event_transaction_id = create_new_event_transaction_id()
        set_event_transaction_type(PROBLEM_SUBMITTED_EVENT_TYPE)
        kwargs = {'modified__range': (modified_start, modified_end), 'module_type': 'problem'}
        if course_id:
            kwargs['course_id'] = course_id
        for record in StudentModule.objects.filter(**kwargs):
            task_args = {
                "user_id": record.student_id,
                "course_id": unicode(record.course_id),
                "usage_id": unicode(record.module_state_key),
                "only_if_higher": False,
                "expected_modified_time": to_timestamp(record.modified),
                "score_deleted": False,
                "event_transaction_id": unicode(event_transaction_id),
                "event_transaction_type": PROBLEM_SUBMITTED_EVENT_TYPE,
                "score_db_table": ScoreDatabaseTableEnum.courseware_student_module,
            }
            recalculate_subsection_grade_v3.apply_async(kwargs=task_args)

        kwargs = {'created_at__range': (modified_start, modified_end)}
        if course_id:
            kwargs['student_item__course_id'] = unicode(course_id)
        for record in Submission.objects.filter(**kwargs):
            task_args = {
                "user_id": user_by_anonymous_id(record.student_item.student_id).id,
                "anonymous_user_id": record.student_item.student_id,
                "course_id": unicode(record.student_item.course_id),
                "usage_id": unicode(record.student_item.item_id),
                "only_if_higher": False,
                "expected_modified_time": to_timestamp(record.created_at),
                "score_deleted": False,
                "event_transaction_id": unicode(event_transaction_id),
                "event_transaction_type": PROBLEM_SUBMITTED_EVENT_TYPE,
                "score_db_table": ScoreDatabaseTableEnum.submissions,
            }
            recalculate_subsection_grade_v3.apply_async(kwargs=task_args)
