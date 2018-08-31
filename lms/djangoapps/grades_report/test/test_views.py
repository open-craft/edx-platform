"""
Tests for the grades_report view
"""
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from lms.djangoapps.courseware.tests.factories import GlobalStaffFactory, StaffFactory
from lms.djangoapps.grades_report.test.test_course import CourseTest
from student.tests.factories import CourseEnrollmentFactory, UserFactory


class GradesReportViewTest(CourseTest, APITestCase):
    """
    Test for thw views of the grades report API
    """
    @classmethod
    def setUpClass(cls):
        super(GradesReportViewTest, cls).setUpClass()
        cls.password = 'test'
        cls.student = UserFactory(username='dummy', password=cls.password)
        cls.other_student = UserFactory(username='foo', password=cls.password)
        cls.other_user = UserFactory(username='bar', password=cls.password)
        cls.staff = StaffFactory(course_key=cls.course.id, password=cls.password)
        cls.global_staff = GlobalStaffFactory.create()
        for user in (cls.student, cls.other_student, ):
            CourseEnrollmentFactory(
                course_id=cls.course.id,
                user=user,
            )

        cls.course_key = cls.course.id
        cls.report_by_section_url = 'grades_report_api:grade_course_report_by_section'
        cls.report_by_assignment_type_url = 'grades_report_api:grade_course_report_by_assignment_type'
        cls.report_enhanced_problem_grade_url = 'grades_report_api:grade_course_report_enhanced_problem_grade'
        cls.report_url = 'grades_report_api:grade_course_report_generated'


    def setUp(self):
        super(GradesReportViewTest, self).setUp()
        self.client.login(username=self.student.username, password=self.password)


    def get_url(self, report_type):
        """
        Helper function to create the url
        """
        base_url = reverse(report_type, args=[self.course_key])
        return base_url


    def test_anonymous(self):
        """
        Test that an anonymous user cannot access the API and an 401 reponse is received.
        """
        self.client.logout()
        response = self.client.get(self.get_url(self.report_by_assignment_type_url))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_json_response(self):
        response = self.client.get(self.get_url(self.report_enhanced_problem_grade_url))
        JSON_CONTENT_TYPE = 'application/json'
        self.assertEqual(response.accepted_media_type, JSON_CONTENT_TYPE)


    def test_report_status_response(self):
        response = self.client.get(self.get_url(self.report_by_section_url))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
