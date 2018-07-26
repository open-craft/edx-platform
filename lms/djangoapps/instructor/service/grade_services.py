from __future__ import division

from student.models import CourseEnrollment

from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.new.course_data import CourseData
from lms.djangoapps.instructor.views.reports_helpers import (
    generate_filtered_sections,
    order_by_section_block,
    calculate_up_to_data_grade,
    delete_unwanted_keys,
    generate_by_at,
    get_course_subsections,
)

from courseware import courses
from opaque_keys.edx.keys import CourseKey


class GradeServices(object):

    def __init__(self, course_id=None):
        if course_id is not None:
            self.course_key = CourseKey.from_string(course_id)
            self.course = courses.get_course_by_id(self.course_key)
            self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)

    def generate(self, course_id, task_input):
        """
        Public method to generate a grade report, by task_type.
        """
        course_string = str(course_id)
        action_name = task_input['task_type']
        if action_name == 'section_report':
            return GradeServices(course_string).by_section(task_input['section_block_id'])

        if action_name == 'enhanced_problem_report':
            return GradeServices(course_string).enhanced_problem_grade()

    def get_grades_by_section(self, section_block_id):
        """
        Public method to get an object with grades data of the course
        If section_block_id is set the calculations will made
        through the all sections till, the selected block_id section.

        Returns:
            1. section_breakdown: Object list with info about all data subsections.
            2. section_filtered: Object list like section_breakdown, but wihtout assignment type grades,
                and dropped subsections.
            3. section_at_breakdown: Object list by section, with assignment types info in that section.
            4. grade_breakdown: Dict with grade info keyed by assigment type.
        """
        all_grades_info = {}
        data = []
        for student in self.students:
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade_factory.summary
            course_data = CourseData(student, course=self.course)
            course_policy = course_data.course.grading_policy
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset = generate_filtered_sections(gradeset)
            gradeset['section_filtered'] = order_by_section_block(gradeset['section_filtered'], course_data)
            gradeset = generate_by_at(gradeset, course_policy)
            gradeset = calculate_up_to_data_grade(gradeset, section_block_id)
            data.append(gradeset)
        all_grades_info["data"] = data
        return all_grades_info

    def by_section(self, section_block_id):
        """
        Public method to generate a dict report with the grades per sections,
        and by assignment type data in that section.

        Returns:
            1. section_at_breakdown: Object list by section, with assignment types info in that section.
            2. up_to_date_grade: Calculated value by student.
        """
        grades_data = self.get_grades_by_section(section_block_id)
        by_section_data = []
        keys_to_delete = ['grade_breakdown', 'section_breakdown', 'section_filtered', 'grade']
        for item in grades_data['data']:
            by_section_data.append(delete_unwanted_keys(item, keys_to_delete))
        return by_section_data

    def enhanced_problem_grade(self):
        """
        Public method to generate a dict report with the enhanced Problem report.

        Returns:
            1. problem_breakdown: Object list contain all problems of the course,
                with the possible and earned points by student.
        """
        all_data_info = {}
        data = []
        for student in self.students:
            gradeset = {}
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset['problem_breakdown'] = get_course_subsections(course_grade_factory.chapter_grades)
            data.append(gradeset)
        all_data_info["data"] = data
        return all_data_info
