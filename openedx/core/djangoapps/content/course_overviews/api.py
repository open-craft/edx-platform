"""
CourseOverview api
"""
import logging

from openedx.core.djangoapps.catalog.api import get_course_run_details
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.content.course_overviews.serializers import (
    CourseOverviewBaseSerializer,
)

log = logging.getLogger(__name__)


def get_course_overview_or_none(course_id):
    """
    Retrieve and return course overview data for the provided course id.

    If the course overview does not exist, return None.
    """
    try:
        return CourseOverview.get_from_id(course_id)
    except CourseOverview.DoesNotExist:
        log.warning(f"Course overview does not exist for {course_id}")
        return None


def get_pseudo_course_overview(course_id):
    """
    Returns a pseudo course overview object for a deleted course.

    Params:
        course_id (CourseKey): The identifier for the course.
    Returns:
        (Temporary) CourseOverview object representing for a deleted course.
    """
    fields = ['title']
    course_run = get_course_run_details(course_id, fields)

    return CourseOverview(
        display_name=course_run.get('title'),
        display_org_with_default=course_id.org,
        certificates_show_before_end=True
    )


def get_course_overviews_from_ids(course_ids):
    """
    Return course overviews for the specified course ids.

    Params:
        course_ids (iterable[CourseKey])

    Returns:
        dict[CourseKey, CourseOverview|None]
    """
    return CourseOverview.get_from_ids(course_ids)


def get_course_overviews(course_ids):
    """
    Return (serialized) course_overview data for a given list of opaque_key course_ids.
    """
    overviews = CourseOverview.objects.filter(id__in=course_ids)
    return CourseOverviewBaseSerializer(overviews, many=True).data
