"""
Management command to backfill default course tabs for all courses. This command is essentially for
when a new default tab is added and we need to update all existing courses. Any new courses will pick
up the new tab automatically via course creation and the CourseTabList.initialize_default method.
People updating to Nutmeg release should run this command as part of the upgrade process.

This should be invoked from the Studio process.

Note: This command will not fail due to updates, but can encounter errors and will log those out.
Search for the error message to detect any issues.
"""
import logging

from django.core.management.base import BaseCommand
from xmodule.tabs import CourseTabList
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

from cms.djangoapps.contentstore.models import BackfillCourseTabsConfig

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Invoke with:
        python manage.py cms backfill_course_tabs
    """
    help = (
        'Backfill default course tabs for all courses. This command is essentially for when a new default '
        'tab is added and we need to update all existing courses. Any new courses will pick up the new '
        'tab automatically via course creation and the CourseTabList.initialize_default method. '
        'Can pass an optional flag --no-publish to skip publishing the courses.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--no-publish', action='store_true', help="Skip publishing courses")

    def handle(self, *args, **options):
        """
        Gathers all course keys in the modulestore and updates the course tabs
        if there are any new default course tabs. Else, makes no updates.
        """
        store = modulestore()
        all_course_keys = sorted(
            (course.id for course in store.get_course_summaries()),
            key=str  # Different types of CourseKeys can't be compared without this.
        )

        config = BackfillCourseTabsConfig.current()
        start = config.start_index if config.enabled and config.start_index >= 0 else 0
        end = (start + config.count) if config.enabled and config.count > 0 else len(all_course_keys)
        course_keys = all_course_keys[start:end]

        logger.info(f'{len(all_course_keys)} courses read from modulestore. Processing {start} to {end}.')

        error_keys = []
        for course_key in course_keys:
            try:
                course = store.get_course(course_key, depth=1)
                existing_tabs = {tab.type for tab in course.tabs}
                CourseTabList.initialize_default(course)
                new_tabs = {tab.type for tab in course.tabs}

                if existing_tabs != new_tabs:
                    logger.info(f'Updating tabs for {course_key}.')
                    if options['no_publish']:
                        # This will update the course block and overview without
                        # triggering course published signal
                        store.update_item(course, ModuleStoreEnum.UserID.mgmt_command, no_signals=True)
                        CourseOverview.load_from_module_store(course.id)
                    else:
                        # This will trigger the Course Published Signal
                        store.update_item(course, ModuleStoreEnum.UserID.mgmt_command)
                    logger.info(f'Successfully updated tabs for {course_key}.')
            except Exception as err:  # pylint: disable=broad-except
                logger.exception(err)
                logger.error(f'Course {course_key} encountered an Exception while trying to update.')
                error_keys.append(course_key)

        if error_keys:
            msg = 'The following courses encountered errors and were not updated:\n'
            for error_key in error_keys:
                msg += f' - {error_key}\n'
            logger.info(msg)
