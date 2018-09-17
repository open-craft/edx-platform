""" File used to generate additional reports data. """
from __future__ import division

from courseware import courses
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades_report.reports_helpers import (
    add_section_info_to_breakdown,
    calculate_up_to_data_grade,
    delete_unwanted_keys,
    generate_by_assignment_type,
    generate_filtered_sections,
    get_course_subsections,
    order_by_section_block
)
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment


class GradeServices(object):
    """
    Util class to generate useful data to be used by
    other reports which edx not supported by now.
    """
    def __init__(self, course_id=None):
        if course_id is not None:
            self.course_key = CourseKey.from_string(course_id)
            self.course = courses.get_course_by_id(self.course_key)
            self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)


    def get_grades_by_section(self, section_block_id=None):
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
            grader_result = course_grade_factory.grader_result
            grader_by_format = course_grade_factory.graded_subsections_by_format
            gradeset = add_section_info_to_breakdown(grader_result, grader_by_format)
            course_policy = course_grade_factory.course_data.course.grading_policy
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset = generate_filtered_sections(gradeset)
            gradeset['section_filtered'] = order_by_section_block(gradeset['section_filtered'], course_grade_factory.course_data)
            gradeset = generate_by_assignment_type(gradeset, course_policy)
            gradeset = calculate_up_to_data_grade(gradeset, section_block_id)
            data.append(gradeset)
        all_grades_info["data"] = data
        return all_grades_info


class BySectionGradeServices(object):
    """
    Class to generate by section grade report.
    """
    def __init__(self, course_id=None):
        self.course_id = course_id


    def by_section(self, section_block_id=None):
        """
        Public method to generate a dict report with the grades per sections,
        and by assignment type data in that section.

        Returns:
            1. grades: Object list by section.
            2. up_to_date_grade: Calculated value by student.
        """
        grades_data = GradeServices(self.course_id).get_grades_by_section(section_block_id)
        by_section_data = []
        keys_to_delete = [
            'grade_breakdown',
            'section_breakdown',
            'section_filtered',
            'assignment_types'
        ]
        for item in grades_data['data']:
            by_section_data.append(delete_unwanted_keys(item, keys_to_delete))
        return by_section_data


class ByAssignmentTypeGradeServices(object):
    """
    Class to generate by assignment type grade report.
    """
    def __init__(self, course_id=None):
        self.course_id = course_id


    def by_assignment_type(self, section_block_id=None):
        """
        Public method to generate a dict report with the grades by assignment type.

        Returns:
            1. grades: Object list by section, with assignment types info in that section.
        """
        grades_data = GradeServices(self.course_id).get_grades_by_section(section_block_id)
        by_section_data = []
        keys_to_delete = [
            'grade_breakdown',
            'section_breakdown',
            'section_filtered',
            'up_to_date_grade'
        ]
        for item in grades_data['data']:
            by_section_data.append(delete_unwanted_keys(item, keys_to_delete))
        return by_section_data


class EnhancedProblemGradeServices(object):
    """
    Class to generate enhanced problem grade report.
    """
    def __init__(self, course_id=None):
        self.course_id = course_id


    def enhanced_problem_grade(self):
        """
        Public method to generate a dict report with the enhanced Problem report.

        Returns:
            1. problem_breakdown: Object list contain all problems of the course,
                with the possible and earned points by student.
        """
        grade_services = GradeServices(self.course_id)
        data = []
        for student in grade_services.students:
            gradeset = {}
            course_grade_factory = CourseGradeFactory().create(student, grade_services.course)
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset['problem_breakdown'] = get_course_subsections(course_grade_factory.chapter_grades)
            data.append(gradeset)
        return data
