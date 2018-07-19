import json
import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from mock import MagicMock, Mock, patch

from lms.djangoapps.instructor.service.grade_services import GradeServices
from lms.djangoapps.instructor.views.reports_helpers import (
    DictList,
    proccess_headers,
    proccess_grades_dict,
    sum_dict_values,
    order_list,
    generate_csv,
    assign_grades,
)


class ServiceGradesTestCase(TestCase):

    def setUp(self):
        create_user = User.objects.create(username='staff', first_name='Staff', last_name='Edx')

        self.user = User.objects.get(username='staff')
        self.course = 'course-v1:Edunext+ED101+2014_T1'
        self.headers = ['username', 'fullname']

        self.course_policy = {
            'Lab': {'droppables': 1, 'total_number': 2, 'weight': 0.15},
            'Homework': {'droppables': 2, 'total_number': 3, 'weight': 0.15},
            'Midterm Exam': {'droppables': 0, 'total_number': 2, 'weight': 0.7}
        }

        self.grades_dict = {
            'username': self.user,
            'general_grade': 0.85,
            'fullname': self.user.get_full_name(),
            'Section 1': [{'Homework': 0.0}, {'Homework': 0.0}, {'Lab': 0.0}],
            'Section 2': [{'Homework': 0.15}, {'Lab': 0.0}, {'Midterm Exam': 0.7}],
            'Section 3': [{'Midterm Exam': 0.7}]
        }

    def test_sum_general_grade(self):
        """
        Test if a sum of all sections is equals to the final grade.
        """
        general_grade = self.grades_dict['general_grade']
        # We need to sum only the grades.
        del self.grades_dict['username']
        del self.grades_dict['general_grade']
        del self.grades_dict['fullname']

        calculation = proccess_grades_dict(self.grades_dict, self.course_policy)
        sum_calculation = sum(calculation)
        return self.assertEqual(sum_calculation, general_grade)

    def test_calculate_grade_by_section(self):
        """
        Report by section sum each subsection with the same assignment typ
        and calculate the grades taking the droppables and the total numbers.
        This test check if these calculations are well structured.
        """
        final_grades = {
            'username': self.user,
            'general_grade': 0.85,
            'fullname': self.user.get_full_name(),
            'Section 1': 0.0,
            'Section 2': 0.5,
            'Section 3': 0.35
        }

        calculation = proccess_grades_dict(self.grades_dict, self.course_policy)
        return self.assertEqual(calculation, final_grades.values())
