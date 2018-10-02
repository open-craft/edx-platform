""" File used to generate additional reports data. """
from __future__ import absolute_import

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
    Class to retrieve useful data to be used
    in "By Section" and "By Assignment Type" report classes which lms doesn't support.
    """
    def __init__(self, course_id=None):
        if course_id is not None:
            self.course_key = CourseKey.from_string(course_id)
            self.course = courses.get_course_by_id(self.course_key)
            self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)


    def get_grades_data(self, section_block_id=None):
        """
        Method to get grades data by student.

        If section_block_id is set,
        the up-to-date-grade calc will be made it up to the section block_id.

        Returns an object with key 'data' and its value is a list per student that contains:
            1. username: Student username
            2. up_to_date_grade: Object that contains the keys 'percent' and 'calculated_until_section'.
            3. percent: The total grade percentage of the student.
            4. grade_breakdown: Dict that contains grade info by assigment type.
            5. section_breakdown: List that contains all subsections grades data.
            6. section_filtered: List equal to section_breakdown, but wihtout assignment type grades averages,
                and dropped subsections.
            7. fullname: Student fullname
            8. section_grades: List that contains all sections, with grades data and
                assignment types of that section.
            9. status: Could take either, 'OK' which means that operation was succesfull or the error message.
        """
        data = []
        course_policy = self.course.grading_policy
        for student, course_grade, error in CourseGradeFactory().iter(self.students, self.course):
            gradeset = {
                'username': student.username,
                'fullname': student.get_full_name(),
                'section_breakdown': [],
                'section_filtered': [],
                'section_grades': [],
                'up_to_date_grade': {},
                'grade_breakdown': {},
                'percent': '',
                'status': ''
            }
            if not course_grade:
                gradeset['status'] = error
            else:
                gradeset.update(add_section_info_to_breakdown(
                    course_grade.grader_result,
                    course_grade.graded_subsections_by_format
                ))
                gradeset['section_filtered'] = generate_filtered_sections(gradeset)
                gradeset['section_filtered'] = order_by_section_block(
                    gradeset['section_filtered'],
                    course_grade.course_data
                )
                gradeset['section_grades'] = generate_by_assignment_type(gradeset, course_policy)
                gradeset['up_to_date_grade'] = calculate_up_to_data_grade(gradeset, section_block_id)
                gradeset['status'] = 'OK'
            data.append(gradeset)
        return data


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
        grades_data = GradeServices(self.course_id).get_grades_data(section_block_id)
        by_section_data = []
        keys_to_delete = [
            'grade_breakdown',
            'section_breakdown',
            'section_filtered',
            'assignment_types'
        ]
        for item in grades_data:
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
        grades_data = GradeServices(self.course_id).get_grades_data(section_block_id)
        if 'error' in grades_data:
            return grades_data
        by_section_data = []
        keys_to_delete = [
            'grade_breakdown',
            'section_breakdown',
            'section_filtered',
            'up_to_date_grade'
        ]
        for item in grades_data:
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
        for student, course_grade, error in CourseGradeFactory().iter(grade_services.students, grade_services.course):
            if error is None:
                gradeset = {}
                gradeset['username'] = student.username
                gradeset['fullname'] = student.get_full_name()
                gradeset['problem_breakdown'] = get_course_subsections(course_grade.chapter_grades)
                data.append(gradeset)
            else:
                error_message = 'There was an error getting the course graders: {}'.format(error)
                data = {'error': error_message}
                return data
        return data
