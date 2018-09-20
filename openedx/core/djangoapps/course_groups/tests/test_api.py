"""
Tests for Cohort API
"""

import tempfile

import ddt
from django.core.files import File
from django.test import RequestFactory
from django.urls import reverse
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import ToyCourseFactory

from lms.djangoapps.courseware.courseware_access_exception import CoursewareAccessException
from openedx.core.djangoapps.course_groups import cohorts
from openedx.core.djangoapps.course_groups.views import api_cohort_settings, api_cohort_handler, api_cohort_users

USERNAME = 'honor'
USER_MAIL = 'honor@example.com'
SETTINGS_PAYLOAD = '{"is_cohorted": true}'
HANDLER_POST_PAYLOAD = '{"name":"Default","user_count":0,"assignment_type":"random","user_partition_id":null\
,"group_id":null}'
HANDLER_PATCH_PAYLOAD = '{"name":"Default Group","group_id":null,"user_partition_id":null,"assignment_type":"random"}'
ADD_USER_PAYLOAD = 'users={}'.format(USER_MAIL)
REMOVE_USER_PAYLOAD = 'username={}'.format(USERNAME)
CSV_DATA = '''email,cohort\n{},DEFAULT'''.format(USER_MAIL)


@ddt.ddt
class TestCohortApi(SharedModuleStoreTestCase):
    """
    Tests for cohort API endpoints
    """

    @classmethod
    def setUpClass(cls):
        super(TestCohortApi, cls).setUpClass()
        cls.request_factory = RequestFactory()
        cls.user = UserFactory(username=USERNAME, email=USER_MAIL)
        cls.staff_user = UserFactory(is_staff=True)
        cls.course_key = ToyCourseFactory.create().id
        cls.course_str = unicode(cls.course_key)

    @ddt.data({'is_staff': True, 'payload': '', 'status': 200},
              {'is_staff': False, 'payload': '', 'status': 404},
              {'is_staff': True, 'payload': SETTINGS_PAYLOAD, 'status': 200},
              {'is_staff': False, 'payload': SETTINGS_PAYLOAD, 'status': 404})
    @ddt.unpack
    def test_cohort_settings(self, is_staff, payload, status):
        """
        Test GET and PATCH methods of cohort settings endpoint
        """
        path = reverse('api_cohorts:cohort_settings', kwargs={'course_key_string': self.course_str})
        if payload:
            request = self.request_factory.patch(
                path=path,
                data=payload,
                content_type='application/json')
        else:
            request = self.request_factory.get(path=path)
        request.user = self.staff_user if is_staff else self.user
        try:
            assert api_cohort_settings(request, self.course_str).status_code == status
        except CoursewareAccessException:
            assert status == 404

    @ddt.data({'is_staff': False, 'payload': HANDLER_POST_PAYLOAD, 'status': 404},
              {'is_staff': True, 'payload': HANDLER_POST_PAYLOAD, 'status': 200},
              {'is_staff': False, 'payload': '', 'status': 404},
              {'is_staff': True, 'payload': '', 'status': 200}, )
    @ddt.unpack
    def test_cohort_handler_create(self, is_staff, payload, status):
        """
        Test GET and POST methods of cohort handler endpoint
        """
        path = reverse('api_cohorts:cohort_handler', kwargs={'course_key_string': self.course_str})
        if payload:
            request = self.request_factory.patch(
                path=path,
                data=payload,
                content_type='application/json')
        else:
            request = self.request_factory.get(path=path)
        request.user = self.staff_user if is_staff else self.user
        try:
            assert api_cohort_handler(request, self.course_str).status_code == status
        except CoursewareAccessException:
            assert status == 404

    @ddt.data({'is_staff': False, 'payload': HANDLER_PATCH_PAYLOAD, 'status': 404},
              {'is_staff': True, 'payload': HANDLER_PATCH_PAYLOAD, 'status': 200},
              {'is_staff': False, 'payload': '', 'status': 404},
              {'is_staff': True, 'payload': '', 'status': 200}, )
    @ddt.unpack
    def test_cohort_handler_patch(self, is_staff, payload, status):
        """
        Test GET and PATCH methods of cohort handler endpoint for a specific cohort
        """
        cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        cohort_id = 1
        path = reverse('api_cohorts:cohort_handler', kwargs={'course_key_string': self.course_str, 'cohort_id': cohort_id})
        if payload:
            request = self.request_factory.patch(
                path=path,
                data=payload,
                content_type='application/json')
        else:
            request = self.request_factory.get(path=path)
        request.user = self.staff_user if is_staff else self.user
        try:
            assert api_cohort_handler(request, self.course_str, cohort_id).status_code == status
        except CoursewareAccessException:
            assert status == 404

    @ddt.data({'is_staff': False, 'payload': ADD_USER_PAYLOAD, 'status': 404},
              {'is_staff': True, 'payload': ADD_USER_PAYLOAD, 'status': 200}, )
    @ddt.unpack
    def test_add_users_to_cohort(self, is_staff, payload, status):
        """
        Test POST method for adding users to a cohort
        """
        cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': self.course_str, 'cohort_id': cohort_id})
        request = self.request_factory.post(
            path=path,
            data=payload,
            content_type='application/x-www-form-urlencoded')
        request.user = self.staff_user if is_staff else self.user
        try:
            assert api_cohort_users(request, self.course_str, cohort_id).status_code == status
        except CoursewareAccessException:
            assert status == 404

    @ddt.data({'is_staff': False, 'payload': REMOVE_USER_PAYLOAD, 'status': 404},
              {'is_staff': True, 'payload': REMOVE_USER_PAYLOAD, 'status': 200}, )
    @ddt.unpack
    def test_remove_user_from_cohort(self, is_staff, payload, status):
        """
        Test POST method for removing an user from a cohort
        """
        cohort = cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        cohorts.add_user_to_cohort(cohort, USERNAME)
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': self.course_str, 'cohort_id': cohort_id})
        request = self.request_factory.delete(
            path=path,
            data=payload,
            content_type='application/x-www-form-urlencoded')
        request.user = self.staff_user if is_staff else self.user
        try:
            assert api_cohort_users(request, self.course_str, cohort_id).status_code == status
        except CoursewareAccessException:
            assert status == 404

    @ddt.data({'is_staff': False, 'payload': CSV_DATA, 'status': 404},
              {'is_staff': True, 'payload': CSV_DATA, 'status': 204},
              {'is_staff': True, 'payload': '', 'status': 400},
              {'is_staff': False, 'payload': '', 'status': 404}, )
    @ddt.unpack
    def test_add_users_csv(self, is_staff, payload, status):
        """
        Call `add_users_to_cohorts` with a file generated from `CSV_DATA`
        """
        cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        # this temporary file will be removed in `self.tearDown()`
        __, file_name = tempfile.mkstemp(suffix='.csv', dir=tempfile.mkdtemp())
        with open(file_name, 'w') as file_pointer:
            file_pointer.write(payload.encode('utf-8'))
        path = reverse('api_cohorts:cohort_handler', kwargs={'course_key_string': self.course_str})
        request = self.request_factory.post(path=path)
        request.user = self.staff_user if is_staff else self.user
        with open(file_name, 'r') as file_pointer:
            request.FILES['uploaded-file'] = File(file_pointer)
            try:
                assert api_cohort_handler(request, self.course_str).status_code == status
            except CoursewareAccessException:
                assert status == 404
