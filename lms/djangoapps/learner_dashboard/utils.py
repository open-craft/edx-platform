"""
The utility methods and functions to help the djangoapp logic
"""
from datetime import datetime

import pytz
from student.models import UserProfile
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


FAKE_COURSE_KEY = CourseKey.from_string('course-v1:fake+course+run')


def strip_course_id(path):
    """
    The utility function to help remove the fake
    course ID from the url path
    """
    course_id = unicode(FAKE_COURSE_KEY)
    return path.split(course_id)[0]


def disclaimer_incomplete_fields_notification(request):
    """
    Get the list of fields that are considered as additional but required.
    If one of these fields are empty, then calculate the numbers of days
    between the joined date and the current day to decide whether to display or not
    the alert after a certain number of days passed from settings or site_configurations.
    """

    days_passed_threshold = configuration_helpers.get_value(
        'DAYS_PASSED_TO_ALERT_PROFILE_INCOMPLETION',
    )
    user_profile = UserProfile.objects.get(user_id=request.user.id)
    joined = user_profile.user.date_joined
    current = datetime.now(pytz.utc)
    delta = current - joined

    if delta.days > days_passed_threshold:
        additional_fields = configuration_helpers.get_value(
            'FIELDS_TO_CHECK_PROFILE_COMPLETION',
        )
        for field_name in additional_fields:
            if not getattr(user_profile, field_name, None):
                return True

    return False
