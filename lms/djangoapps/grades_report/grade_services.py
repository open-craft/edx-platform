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
        the up-to-date-grade calc will be made up to the section block_id.

        Returns an object with key 'data' and its value is a list per student that contains:
            1. username: Student username.
            2. up_to_date_grade: Object that contains the keys 'percent' and 'calculated_until_section'.
            3. percent: The total grade percentage of the student.
            4. grade_breakdown: Dict that contains grade info by assigment type.
            5. section_breakdown: List that contains all subsections grades data.
            6. section_filtered: List equal to section_breakdown, but wihtout assignment type grades averages,
                and dropped subsections.
            7. fullname: Student fullname.
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
                'status': 'OK'
            }
            if not course_grade:
                gradeset['status'] = error
            else:
                # Setting up the 'section_breakdown', 'percent' and 'grade_breakdown' keys.
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
            data.append(gradeset)
        return data


class BySectionGradeServices(object):
    """
    Class to generate a new grade report per course sections.
    """
    def __init__(self, course_id=None):
        self.course_id = course_id


    def generate_grade_report_by_section(self, section_block_id=None):
        """
        Generate a List object that contains all students enrolled in the course,
        and their grades in each section of the course and the 'up-to-date-grade' object.

        The 'up-to-date-grade' calc will be made up to the section_block_id if given,
        if not, the calculation will be made in all sections of the course.

        We need to clean up some data keys of the object returned by get_grades_data(),
        since they will not need it anymore in the data of the final report.

        Returns a List object per student that contains:
            1. username: Student username.
            2. status: Could take either, 'OK' which means that operation was succesfull or a error message.
            3. section_grades: List that contains all sections, with grades data.
            4. up_to_date_grade: Object that contains the keys 'percent' and 'calculated_until_section'.
            5. percent: The total grade percentage of the student.
            6. fullname: Student fullname.
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
    Class to generate a new grade report per course sections,
    and the assignments types setting in each section.
    """
    def __init__(self, course_id=None):
        self.course_id = course_id


    def generate_grade_report_by_assignment_type(self, section_block_id=None):
        """
        Generate a List object that contains all students enrolled in the course,
        and their grades by section and assignment type.

        The 'up-to-date-grade' calc will be made up to the section_block_id if given,
        if not, the calculation will be made in all sections of the course.

        We need to clean up some data keys of the object returned by get_grades_data(),
        since they will not need it anymore in the data of the final report.

        Returns a List object per student that contains:
            1. username: Student username.
            2. status: Could take either, 'OK' which means that operation was succesfull or a error message.
            3. section_grades: List that contains all sections, with grades data
                and assignment type grades in each section.
            4. up_to_date_grade: Object that contains the keys 'percent' and 'calculated_until_section'.
            5. percent: The total grade percentage of the student.
            6. fullname: Student fullname.
        """
        grades_data = GradeServices(self.course_id).get_grades_data(section_block_id)
        by_section_data = []
        keys_to_delete = [
            'grade_breakdown',
            'section_breakdown',
            'section_filtered'
        ]
        for item in grades_data:
            by_section_data.append(delete_unwanted_keys(item, keys_to_delete))
        return by_section_data


class ProblemGradeServices(object):
    """
    Class to generate a 'enhanced' problem grade report.
    """
    def __init__(self, course_id=None):
        self.course_key = CourseKey.from_string(course_id)
        self.course = courses.get_course_by_id(self.course_key)
        self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)


    def generate_problem_grade_report(self):
        """
        Generate a List object that contains all students enrolled in the course
        with the score data of each problem in the course.

        This grade report is generated in the same order of the course
        according to the section - subsection pairs,
        instead of the assignment type they belongs to.

        Returns a List object per student that contains:
            1. username: Student username.
            2. problem_breakdown: List object that contains each course problem and their score.
            3. fullname: Student fullname.
            4. status: Could take either, 'OK' which means that operation was succesfull or error message.
        """
        data = []
        for student, course_grade, error in CourseGradeFactory().iter(self.students, self.course):
            problem_grade_set = {
                'username': student.username,
                'fullname': student.get_full_name(),
                'problem_breakdown': [],
                'status': 'OK'
            }
            if not course_grade:
                problem_grade_set['status'] = error
            else:
                problem_grade_set['problem_breakdown'] = get_course_subsections(course_grade.chapter_grades)
            data.append(problem_grade_set)
        return data
