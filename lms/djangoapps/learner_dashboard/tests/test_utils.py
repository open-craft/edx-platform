"""
Unit test module covering utils module
"""

import ddt

from datetime import date, datetime

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

import pytz

from student.models import UserProfile

from lms.djangoapps.learner_dashboard import utils


@ddt.ddt
class TestUtils(TestCase):
    """
    The test case class covering the all the utils functions
    """
    @ddt.data('path1/', '/path1/path2/', '/', '')
    def test_strip_course_id(self, path):
        """
        Test to make sure the function 'strip_course_id'
        handles various url input
        """
        actual = utils.strip_course_id(path + unicode(utils.FAKE_COURSE_KEY))
        self.assertEqual(actual, path)


class DisclaimerIncompleteFieldsTestCase(TestCase):
    """
    Test cases to display or not the reminder alert if a user
    has left some required fields in blank after n days.
    """

    def setUp(self):
        self.user = User.objects.create(
            username='my_self_user',
            date_joined=date(2016, 3, 1)
        )
        self.user_profile = UserProfile.objects.create(
            user_id=self.user.id,
            year_of_birth=1989
        )

    @override_settings(FEATURES={"DAYS_PASSED_TO_ALERT_PROFILE_INCOMPLETION": 5})
    @override_settings(FEATURES={"FIELDS_TO_CHECK_PROFILE_COMPLETION": ['gender', 'city', 'year_of_birth']})
    def test_showing_alert(self):
        """
        Test the case when the alert should be displayed, due to the user created only having one
        additional field filled.
        """
        display_alert = utils.disclaimer_incomplete_fields_notification(self.user_profile)
        return self.assertEqual(display_alert, True)

    @override_settings(FEATURES={"DAYS_PASSED_TO_ALERT_PROFILE_INCOMPLETION": 10})
    @override_settings(FEATURES={"FIELDS_TO_CHECK_PROFILE_COMPLETION": ['year_of_birth']})
    def test_not_showing_alert(self):
        """
        Test the case when the alert should not be displayed, due to in settings we are just
        passing the field that is filled.
        """
        display_alert = utils.disclaimer_incomplete_fields_notification(self.user_profile)
        return self.assertEqual(display_alert, False)

    @override_settings(FEATURES={"DAYS_PASSED_TO_ALERT_PROFILE_INCOMPLETION": 5})
    @override_settings(FEATURES={"FIELDS_TO_CHECK_PROFILE_COMPLETION": []})
    def test_not_showing_alert_no_fields(self):
        """
        Test the case when the alert should be displayed, due to the user created only having one
        additional field filled.
        """
        display_alert = utils.disclaimer_incomplete_fields_notification(self.user_profile)
        return self.assertEqual(display_alert, False)

    @override_settings(FEATURES={"DAYS_PASSED_TO_ALERT_PROFILE_INCOMPLETION": 5})
    @override_settings(FEATURES={"FIELDS_TO_CHECK_PROFILE_COMPLETION": []})
    def test_not_showing_alert_invalid_period(self):
        """
        Test the case when the alert should be displayed, due to the user created only having one
        additional field filled.
        """
        current = datetime.now(pytz.utc)
        User.objects.filter(username='my_self_user').update(date_joined=current)
        display_alert = utils.disclaimer_incomplete_fields_notification(self.user_profile)
        return self.assertEqual(display_alert, False)
