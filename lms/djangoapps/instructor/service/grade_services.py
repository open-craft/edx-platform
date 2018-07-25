from __future__ import division
import json

from student.models import CourseEnrollment

from lms.djangoapps.grades.context import grading_context_for_course
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.new.course_data import CourseData
from lms.djangoapps.instructor.views.reports_helpers import (
    generate_filtered_sections,
    order_by_section_block,
    calculate_up_to_data_grade,
    delete_unwanted_keys,
    generate_by_at,
)

from courseware import courses
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.django import modulestore


class GradeServices(object):

    def __init__(self, course_id=None):
        if course_id is not None:
            self.course_string = course_id
            self.course_key = CourseKey.from_string(course_id)
            self.course = courses.get_course_by_id(self.course_key)
            self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)
            self.headers = ['username', 'fullname']

    def generate(self, course_id, task_input):
        """
        Public method to generate a grade report.
        """
        course_string = str(course_id)
        action_name = task_input['task_type']
        if action_name == 'section_report':
            return GradeServices(course_string).by_section(task_input['section_block_id'])

        if action_name == 'assignment_type_report':
            return GradeServices(course_string).by_section(task_input['section_block_id'])

        if action_name == 'enhanced_problem_report':
            raise NotImplementedError
            # return GradeServices(course_string).enhanced_problem_grade()


    def get_grades_by_section(self, section_block_id):

        all_grades_info = {}
        data = []
        for student in self.students:
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade_factory.summary
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset = generate_filtered_sections(gradeset)
            gradeset['section_filtered'] = order_by_section_block(gradeset['section_filtered'])
            course_data = CourseData(student, course=self.course)
            course_policy = course_data.course.grading_policy
            gradeset = generate_by_at(gradeset, course_policy)
            up_to_date_grade = calculate_up_to_data_grade(gradeset, section_block_id)
            data.append(gradeset)
        all_grades_info["data"] = data
        return all_grades_info


    def by_section(self, section_block_id):
        """
        Public method to generate a json report with the grades per sections.
        """
        grades_data = self.get_grades_by_section(section_block_id)
        by_section_data = []
        keys_to_delete = ['grade_breakdown', 'section_breakdown', 'section_filtered', 'grade']
        for item in grades_data['data']:
            by_section_data.append(delete_unwanted_keys(item, keys_to_delete))
        return by_section_data
