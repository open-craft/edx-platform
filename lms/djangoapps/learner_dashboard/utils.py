"""
The utility methods and functions to help the djangoapp logic
"""
import datetime

from datetime import date

from django.conf import settings
from django.contrib.auth.models import User

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


def disclaimer_incomplete_fields_notification(self, request):
    days_passed = 7
    user = User.objects.get(username=request.user.username)
    joined = user.date_joined
    current = datetime.datetime.now()

    joined_date = date(joined.year, joined.month, joined.day)
    current_date = date(current.year, current.month, current.day)
    delta = joined_date - current_date

    if delta.days > days_passed:
        pass
