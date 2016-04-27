# -*- coding: utf-8 -*-
"""
Unit tests for the Bulk Enrollment API
"""
import json

import ddt
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test import RequestFactory
from mock import patch
from nose.plugins.attrib import attr

from courseware.tests.factories import InstructorFactory
from courseware.tests.helpers import LoginEnrollmentTestCase
from instructor.views.api import common_exceptions_400
from instructor_task.api_helper import AlreadyRunningError
from microsite_configuration import microsite
from student.models import (
    CourseEnrollment, CourseEnrollmentAllowed, ManualEnrollmentAudit, UNENROLLED_TO_ENROLLED, ENROLLED_TO_UNENROLLED,
    ALLOWEDTOENROLL_TO_UNENROLLED, ENROLLED_TO_ENROLLED, UNENROLLED_TO_ALLOWEDTOENROLL,
    UNENROLLED_TO_UNENROLLED, ALLOWEDTOENROLL_TO_ENROLLED
)
from student.roles import CourseInstructorRole
from student.tests.factories import UserFactory, CourseModeFactory
from xmodule.fields import Date
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

DATE_FIELD = Date()


@common_exceptions_400
def view_success(request):  # pylint: disable=unused-argument
    "A dummy view for testing that returns a simple HTTP response"
    return HttpResponse('success')


@common_exceptions_400
def view_user_doesnotexist(request):  # pylint: disable=unused-argument
    "A dummy view that raises a User.DoesNotExist exception"
    raise User.DoesNotExist()


@common_exceptions_400
def view_alreadyrunningerror(request):  # pylint: disable=unused-argument
    "A dummy view that raises an AlreadyRunningError exception"
    raise AlreadyRunningError()


@attr('shard_1')
@ddt.ddt
class TestInstructorAPIEnrollment(ModuleStoreTestCase, LoginEnrollmentTestCase):
    """
    Test enrollment modification endpoint.

    This test does NOT exhaustively test state changes, that is the
    job of test_enrollment. This tests the response and action switch.
    """

    def setUp(self):
        super(TestInstructorAPIEnrollment, self).setUp()

        self.request = RequestFactory().request()
        self.course = CourseFactory.create()
        self.course_key = self.course.id.to_deprecated_string()
        self.instructor = InstructorFactory(course_key=self.course.id)
        self.client.login(username=self.instructor.username, password='test')

        self.enrolled_student = UserFactory(username='EnrolledStudent', first_name='Enrolled', last_name='Student')
        CourseEnrollment.enroll(
            self.enrolled_student,
            self.course.id
        )
        self.notenrolled_student = UserFactory(username='NotEnrolledStudent', first_name='NotEnrolled',
                                               last_name='Student')

        # Create invited, but not registered, user
        cea = CourseEnrollmentAllowed(email='robot-allowed@robot.org', course_id=self.course.id)
        cea.save()
        self.allowed_email = 'robot-allowed@robot.org'

        self.notregistered_email = 'robot-not-an-email-yet@robot.org'
        self.assertEqual(User.objects.filter(email=self.notregistered_email).count(), 0)

        # Email URL values
        self.site_name = microsite.get_value(
            'SITE_NAME',
            settings.SITE_NAME
        )
        self.about_path = '/courses/{}/about'.format(self.course.id)
        self.course_path = '/courses/{}/'.format(self.course.id)

        # uncomment to enable enable printing of large diffs
        # from failed assertions in the event of a test failure.
        # (comment because pylint C0103(invalid-name))
        self.maxDiff = None

    def test_missing_params(self):
        """ Test missing all query parameters. """
        url = reverse('bulk_enroll')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)

    def test_bad_action(self):
        """ Test with an invalid action. """
        action = 'robot-not-an-action'
        url = reverse('bulk_enroll')
        response = self.client.post(
            url,
            {
                'identifiers': self.enrolled_student.email,
                'action': action,
                'courses': self.course_key,
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_email(self):
        url = reverse('bulk_enroll')
        response = self.client.post(
            url,
            {
                'identifiers': 'percivaloctavius@',
                'action': 'enroll',
                'email_students': False,
                'courses': self.course_key,
            }
        )
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "enroll",
            'auto_enroll': False,
            'email_students': False,
            "courses": {
                self.course_key: {
                    "action": "enroll",
                    'auto_enroll': False,
                    "results": [
                        {
                            "identifier": 'percivaloctavius@',
                            "invalidIdentifier": True,
                        }
                    ]
                }
            }
        }

        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_invalid_username(self):
        url = reverse('bulk_enroll')
        response = self.client.post(
            url,
            {
                'identifiers': 'percivaloctavius',
                'action': 'enroll',
                'email_students': False,
                'courses': self.course_key,
            }
        )
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "enroll",
            'auto_enroll': False,
            'email_students': False,
            "courses": {
                self.course_key: {
                    "action": "enroll",
                    'auto_enroll': False,
                    "results": [
                        {
                            "identifier": 'percivaloctavius',
                            "invalidIdentifier": True,
                        }
                    ]
                }
            }
        }

        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_enroll_with_username(self):
        url = reverse('bulk_enroll')
        response = self.client.post(
            url,
            {
                'identifiers': self.notenrolled_student.username,
                'action': 'enroll',
                'email_students': False,
                'courses': self.course_key,
            }
        )
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "enroll",
            'auto_enroll': False,
            "email_students": False,
            "courses": {
                self.course_key: {
                    "action": "enroll",
                    'auto_enroll': False,
                    "results": [
                        {
                            "identifier": self.notenrolled_student.username,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ENROLLED)
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_enroll_without_email(self):
        url = reverse('bulk_enroll')
        response = self.client.post(
            url,
            {
                'identifiers': self.notenrolled_student.email,
                'action': 'enroll',
                'email_students': False,
                'courses': self.course_key,
            }
        )
        print "type(self.notenrolled_student.email): {}".format(type(self.notenrolled_student.email))
        self.assertEqual(response.status_code, 200)

        # test that the user is now enrolled
        user = User.objects.get(email=self.notenrolled_student.email)
        self.assertTrue(CourseEnrollment.is_enrolled(user, self.course.id))

        # test the response data
        expected = {
            "action": "enroll",
            "auto_enroll": False,
            "email_students": False,
            "courses": {
                self.course_key: {
                    "action": "enroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.notenrolled_student.email,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ENROLLED)
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 0)

    @ddt.data('http', 'https')
    def test_enroll_with_email(self, protocol):
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notenrolled_student.email, 'action': 'enroll', 'email_students': True,
                  'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)

        print "type(self.notenrolled_student.email): {}".format(type(self.notenrolled_student.email))
        self.assertEqual(response.status_code, 200)

        # test that the user is now enrolled
        user = User.objects.get(email=self.notenrolled_student.email)
        self.assertTrue(CourseEnrollment.is_enrolled(user, self.course.id))

        # test the response data
        expected = {
            "action": "enroll",
            "auto_enroll": False,
            "email_students": True,
            "courses": {
                self.course_key: {
                    "action": "enroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.notenrolled_student.email,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            u'You have been enrolled in {}'.format(self.course.display_name)
        )
        self.assertEqual(
            mail.outbox[0].body,
            "Dear NotEnrolled Student\n\nYou have been enrolled in {} "
            "at edx.org by a member of the course staff. "
            "The course should now appear on your edx.org dashboard.\n\n"
            "To start accessing course materials, please visit "
            "{proto}://{site}{course_path}\n\n----\n"
            "This email was automatically sent from edx.org to NotEnrolled Student".format(
                self.course.display_name,
                proto=protocol, site=self.site_name, course_path=self.course_path
            )
        )

    @ddt.data('http', 'https')
    def test_enroll_with_email_not_registered(self, protocol):
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': True,
                  'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ALLOWEDTOENROLL)
        self.assertEqual(response.status_code, 200)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            u'You have been invited to register for {}'.format(self.course.display_name)
        )
        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {} at edx.org by a member of the course staff.\n\n"
            "To finish your registration, please visit {proto}://{site}/register and fill out the "
            "registration form making sure to use robot-not-an-email-yet@robot.org in the E-mail field.\n"
            "Once you have registered and activated your account, "
            "visit {proto}://{site}{about_path} to join the course.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                self.course.display_name, proto=protocol, site=self.site_name, about_path=self.about_path
            )
        )

    @ddt.data('http', 'https')
    @patch.dict(settings.FEATURES, {'ENABLE_MKTG_SITE': True})
    def test_enroll_email_not_registered_mktgsite(self, protocol):
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': True,
                  'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ALLOWEDTOENROLL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {display_name}"
            " at edx.org by a member of the course staff.\n\n"
            "To finish your registration, please visit {proto}://{site}/register and fill out the registration form "
            "making sure to use robot-not-an-email-yet@robot.org in the E-mail field.\n"
            "You can then enroll in {display_name}.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                display_name=self.course.display_name, proto=protocol, site=self.site_name
            )
        )

    @ddt.data('http', 'https')
    def test_enroll_with_email_not_registered_autoenroll(self, protocol):
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': True,
                  'auto_enroll': True, 'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)
        print "type(self.notregistered_email): {}".format(type(self.notregistered_email))
        self.assertEqual(response.status_code, 200)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            u'You have been invited to register for {}'.format(self.course.display_name)
        )
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ALLOWEDTOENROLL)
        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {display_name}"
            " at edx.org by a member of the course staff.\n\n"
            "To finish your registration, please visit {proto}://{site}/register and fill out the registration form "
            "making sure to use robot-not-an-email-yet@robot.org in the E-mail field.\n"
            "Once you have registered and activated your account,"
            " you will see {display_name} listed on your dashboard.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                proto=protocol, site=self.site_name, display_name=self.course.display_name
            )
        )

    def test_unenroll_without_email(self):
        url = reverse('bulk_enroll')
        response = self.client.post(url, {'identifiers': self.enrolled_student.email, 'action': 'unenroll',
                                          'email_students': False, 'courses': self.course_key,})
        print "type(self.enrolled_student.email): {}".format(type(self.enrolled_student.email))
        self.assertEqual(response.status_code, 200)

        # test that the user is now unenrolled
        user = User.objects.get(email=self.enrolled_student.email)
        self.assertFalse(CourseEnrollment.is_enrolled(user, self.course.id))

        # test the response data
        expected = {
            "action": "unenroll",
            "auto_enroll": False,
            "email_students": False,
            "courses": {
                self.course_key : {
                    "action": "unenroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.enrolled_student.email,
                            "before": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }

        }

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, ENROLLED_TO_UNENROLLED)
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 0)

    def test_unenroll_with_email(self):
        url = reverse('bulk_enroll')
        response = self.client.post(url, {'identifiers': self.enrolled_student.email, 'action': 'unenroll',
                                          'email_students': True, 'courses': self.course_key,})
        print "type(self.enrolled_student.email): {}".format(type(self.enrolled_student.email))
        self.assertEqual(response.status_code, 200)

        # test that the user is now unenrolled
        user = User.objects.get(email=self.enrolled_student.email)
        self.assertFalse(CourseEnrollment.is_enrolled(user, self.course.id))

        # test the response data
        expected = {
            "action": "unenroll",
            "auto_enroll": False,
            "email_students": True,
            "courses": {
                self.course_key: {
                    "action": "unenroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.enrolled_student.email,
                            "before": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, ENROLLED_TO_UNENROLLED)
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'You have been un-enrolled from {display_name}'.format(display_name=self.course.display_name, )
        )
        self.assertEqual(
            mail.outbox[0].body,
            "Dear Enrolled Student\n\nYou have been un-enrolled in {display_name} "
            "at edx.org by a member of the course staff. "
            "The course will no longer appear on your edx.org dashboard.\n\n"
            "Your other courses have not been affected.\n\n----\n"
            "This email was automatically sent from edx.org to Enrolled Student".format(
                display_name=self.course.display_name,
            )
        )

    def test_unenroll_with_email_allowed_student(self):
        url = reverse('bulk_enroll')
        response = self.client.post(url,
                                    {'identifiers': self.allowed_email, 'action': 'unenroll', 'email_students': True,
                                     'courses': self.course_key,})
        print "type(self.allowed_email): {}".format(type(self.allowed_email))
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "unenroll",
            "auto_enroll": False,
            "email_students": True,
            "courses": {
                self.course_key: {
                    "action": "unenroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.allowed_email,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": False,
                                "allowed": True,
                            },
                            "after": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": False,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, ALLOWEDTOENROLL_TO_UNENROLLED)
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'You have been un-enrolled from {display_name}'.format(display_name=self.course.display_name, )
        )
        self.assertEqual(
            mail.outbox[0].body,
            "Dear Student,\n\nYou have been un-enrolled from course {display_name} by a member of the course staff. "
            "Please disregard the invitation previously sent.\n\n----\n"
            "This email was automatically sent from edx.org to robot-allowed@robot.org".format(
                display_name=self.course.display_name,
            )
        )

    @ddt.data('http', 'https')
    @patch('instructor.enrollment.uses_shib')
    def test_enroll_with_email_not_registered_with_shib(self, protocol, mock_uses_shib):
        mock_uses_shib.return_value = True

        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': True,
                  'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)
        self.assertEqual(response.status_code, 200)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'You have been invited to register for {display_name}'.format(display_name=self.course.display_name, )
        )

        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {display_name} at edx.org by a member of the course staff.\n\n"
            "To access the course visit {proto}://{site}{about_path} and register for the course.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                proto=protocol, site=self.site_name, about_path=self.about_path,
                display_name=self.course.display_name,
            )
        )

    @patch('instructor.enrollment.uses_shib')
    @patch.dict(settings.FEATURES, {'ENABLE_MKTG_SITE': True})
    def test_enroll_email_not_registered_shib_mktgsite(self, mock_uses_shib):
        # Try with marketing site enabled and shib on
        mock_uses_shib.return_value = True

        url = reverse('bulk_enroll')
        # Try with marketing site enabled
        with patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            response = self.client.post(url, {'identifiers': self.notregistered_email, 'action': 'enroll',
                                              'email_students': True, 'courses': self.course_key,})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {} at edx.org by a member of the course staff.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                self.course.display_name,
            )
        )

    @ddt.data('http', 'https')
    @patch('instructor.enrollment.uses_shib')
    def test_enroll_with_email_not_registered_with_shib_autoenroll(self, protocol, mock_uses_shib):
        mock_uses_shib.return_value = True

        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': True,
                  'auto_enroll': True, 'courses': self.course_key,}
        environ = {'wsgi.url_scheme': protocol}
        response = self.client.post(url, params, **environ)
        print "type(self.notregistered_email): {}".format(type(self.notregistered_email))
        self.assertEqual(response.status_code, 200)

        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'You have been invited to register for {display_name}'.format(display_name=self.course.display_name, )
        )

        self.assertEqual(
            mail.outbox[0].body,
            "Dear student,\n\nYou have been invited to join {display_name}"
            " at edx.org by a member of the course staff.\n\n"
            "To access the course visit {proto}://{site}{course_path} and login.\n\n----\n"
            "This email was automatically sent from edx.org to robot-not-an-email-yet@robot.org".format(
                display_name=self.course.display_name,
                proto=protocol, site=self.site_name, course_path=self.course_path
            )
        )

    def test_enroll_already_enrolled_student(self):
        """
        Ensure that already enrolled "verified" students cannot be downgraded
        to "honor"
        """
        course_enrollment = CourseEnrollment.objects.get(
            user=self.enrolled_student, course_id=self.course.id
        )
        # make this enrollment "verified"
        course_enrollment.mode = u'verified'
        course_enrollment.save()
        self.assertEqual(course_enrollment.mode, u'verified')

        # now re-enroll the student through the instructor dash
        self._change_student_enrollment(self.enrolled_student, self.course, 'enroll')

        # affirm that the student is still in "verified" mode
        course_enrollment = CourseEnrollment.objects.get(
            user=self.enrolled_student, course_id=self.course.id
        )
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, ENROLLED_TO_ENROLLED)
        self.assertEqual(course_enrollment.mode, u"verified")

    def create_paid_course(self):
        """
        create paid course mode.
        """
        paid_course = CourseFactory.create()
        CourseModeFactory.create(course_id=paid_course.id, min_price=50)
        CourseInstructorRole(paid_course.id).add_users(self.instructor)
        return paid_course

    def test_reason_field_should_not_be_empty(self):
        """
        test to check that reason field should not be empty when
        manually enrolling the students for the paid courses.
        """
        paid_course = self.create_paid_course()
        paid_course_key = paid_course.id.to_deprecated_string()
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': False,
                  'auto_enroll': False, 'courses': paid_course_key}
        response = self.client.post(url, params)
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 0)

        # test the response data
        expected = {
            "action": "enroll",
            "auto_enroll": False,
            "email_students": False,
            "courses": {
                paid_course_key: {
                    "action": "enroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "error": True
                        }
                    ]
                }
            }
        }
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_unenrolled_allowed_to_enroll_user(self):
        """
        test to unenroll allow to enroll user.
        """
        paid_course = self.create_paid_course()
        paid_course_key = paid_course.id.to_deprecated_string()
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': False,
                  'auto_enroll': False, 'reason': 'testing..', 'courses': paid_course_key}
        response = self.client.post(url, params)
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_ALLOWEDTOENROLL)
        self.assertEqual(response.status_code, 200)

        # now registered the user
        UserFactory(email=self.notregistered_email)
        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'enroll', 'email_students': False,
                  'auto_enroll': False, 'reason': 'testing', 'courses': paid_course_key}
        response = self.client.post(url, params)
        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 2)
        self.assertEqual(manual_enrollments[1].state_transition, ALLOWEDTOENROLL_TO_ENROLLED)
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "enroll",
            "auto_enroll": False,
            "email_students": False,
            "courses": {
                paid_course_key: {
                    "action": "enroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.notregistered_email,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": True,
                            },
                            "after": {
                                "enrollment": True,
                                "auto_enroll": False,
                                "user": True,
                                "allowed": True,
                            }
                        }
                    ]
                }
            }
        }
        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_unenrolled_already_not_enrolled_user(self):
        """
        test unenrolled user already not enrolled in a course.
        """
        paid_course = self.create_paid_course()
        paid_course_key = paid_course.id.to_deprecated_string()
        course_enrollment = CourseEnrollment.objects.filter(
            user__email=self.notregistered_email, course_id=paid_course.id
        )
        self.assertEqual(course_enrollment.count(), 0)

        url = reverse('bulk_enroll')
        params = {'identifiers': self.notregistered_email, 'action': 'unenroll', 'email_students': False,
                  'auto_enroll': False, 'reason': 'testing', 'courses': paid_course_key}

        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 200)

        # test the response data
        expected = {
            "action": "unenroll",
            "auto_enroll": False,
            "email_students": False,
            "courses": {
                paid_course_key: {
                    "action": "unenroll",
                    "auto_enroll": False,
                    "results": [
                        {
                            "identifier": self.notregistered_email,
                            "before": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": False,
                                "allowed": False,
                            },
                            "after": {
                                "enrollment": False,
                                "auto_enroll": False,
                                "user": False,
                                "allowed": False,
                            }
                        }
                    ]
                }
            }
        }

        manual_enrollments = ManualEnrollmentAudit.objects.all()
        self.assertEqual(manual_enrollments.count(), 1)
        self.assertEqual(manual_enrollments[0].state_transition, UNENROLLED_TO_UNENROLLED)

        res_json = json.loads(response.content)
        self.assertEqual(res_json, expected)

    def test_unenroll_and_enroll_verified(self):
        """
        Test that unenrolling and enrolling a student from a verified track
        results in that student being in an honor track
        """
        course_enrollment = CourseEnrollment.objects.get(
            user=self.enrolled_student, course_id=self.course.id
        )
        # upgrade enrollment
        course_enrollment.mode = u'verified'
        course_enrollment.save()
        self.assertEqual(course_enrollment.mode, u'verified')

        self._change_student_enrollment(self.enrolled_student, self.course, 'unenroll')

        self._change_student_enrollment(self.enrolled_student, self.course, 'enroll')

        course_enrollment = CourseEnrollment.objects.get(
            user=self.enrolled_student, course_id=self.course.id
        )
        self.assertEqual(course_enrollment.mode, u'honor')

    def _change_student_enrollment(self, user, course, action):
        """
        Helper function that posts to 'bulk_enroll' to change
        a student's enrollment
        """
        url = reverse('bulk_enroll')
        params = {
            'identifiers': user.email,
            'courses': course.id.to_deprecated_string(),
            'action': action,
            'email_students': True,
            'reason': 'change user enrollment'
        }
        print params
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 200)
        return response
