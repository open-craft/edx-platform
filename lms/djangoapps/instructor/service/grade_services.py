# -*- coding: utf-8 -*-
from __future__ import division
import csv
import json

from student.models import CourseEnrollment

from lms.djangoapps.grades.context import grading_context_for_course
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.new.course_data import CourseData
from lms.djangoapps.instructor.views.reports_helpers import (
    DictList,
    proccess_headers,
    proccess_grades_dict,
    sum_dict_values,
    order_list,
    generate_csv,
    assign_grades,
    ForceNonAtomic,
    remove_dropped_grades,
    get_total_grade_by_section,
    generate_filtered_sections,
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

    def generate(self, _xmodule_instance_args, _entry_id, course_id, _task_input, action_name):
        """
        Public method to generate a grade report.
        """
        course_string = str(course_id)
        task_id = _xmodule_instance_args['task_id']
        from lms.djangoapps.instructor_task.tasks_helper.grades import _CourseGradeReportContext, CourseGradeReport
        with modulestore().bulk_operations(course_id):
            context = _CourseGradeReportContext(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name)

            if action_name == 'section_report':
                return GradeServices(course_string).by_section()

            if action_name == 'assignment_type_report':
                return GradeServices(course_string).by_assignment_type()

            if action_name == 'enhanced_problem_report':
                return GradeServices(course_string).enhanced_problem_grade()


    def get_grades(self):
        """
        Public method to generate custom reports.
        Returns:
            1. Base info of the grades, from this list we could get
               the info thet we require.
            2. Dict with the course policy
        """
        course_grades = []
        result = []
        counter_assignment_type = {}

        for student in self.students:
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade_factory.summary
            gradeset["username"] = course_grade_factory.user
            course_grades.append(gradeset)

            sections = course_grade_factory.chapter_grades
            course_data = CourseData(student, course=self.course)
            course_policy = course_data.course.grading_policy

            for grade in course_grades:
                section_grade = DictList()
                sequentials = DictList()
                section_grade['general_grade'] = grade['percent']
                for student_grade in grade['section_breakdown']:
                    # In graders constructor, we added some additional keys
                    # in the section_breakdown json with the purpose to get the
                    # subsection's parent and be able to differentiate when a grade is
                    # calculated in a single entry. We apply this logic only if
                    # has a subsection object and discard the droppables.
                    if (student_grade.has_key('subsection') and
                        student_grade['subsection'] is not None or
                        student_grade.has_key('only') and not
                        student_grade.has_key('mark')):

                        # Get the parent for each sequential.
                        locator = student_grade['subsection'].location
                        parent = modulestore().get_parent_location(locator)
                        parent_location = modulestore().get_item(parent)

                        assignment_type = student_grade['subsection'].format
                        chapter_name = parent_location.display_name

                        # Since the course_policy that we need is in a list
                        # we take these values and we storage them in a dict for ease
                        # when we need to use it.
                        for policy in course_policy['GRADER']:
                            assignment_type_name = policy['type']
                            weight = policy['weight']
                            droppables = policy['drop_count']
                            total_number = policy['min_count']
                            counter_assignment_type[assignment_type_name] = {
                                'weight': weight,
                                'droppables': droppables,
                                'total_number': total_number
                            }

                            assignment_grades = assign_grades(policy, assignment_type, chapter_name, student_grade, section_grade, sequentials)

            general_grade = assignment_grades['general_grade'][0]
            section_grade.update({'username': student, 'fullname': student.get_full_name(), 'general_grade': general_grade})
            result.append(section_grade)

        return result, counter_assignment_type, sequentials

    def by_section(self):
        """
        Public method to generate a CSV report with the grades per sections.
        """
        self.new_by_section()
        course_grade = self.get_grades()
        section_grades = course_grade[0]
        course_policy = course_grade[1]
        score_by_section = []
        for grades in section_grades:
            for key, value in grades.items():
                self.headers.append(key)
            proccessed_section_grade = proccess_grades_dict(grades, course_policy)
            score_by_section.append(proccessed_section_grade)
        header_rows = proccess_headers(self.headers)
        for items in score_by_section:
            user = items[0]
            items[0] = user.username

        return score_by_section

    def by_assignment_type(self):
        """
        Public method to generate a json report with the grades per assignment type.
        """
        course_grade = self.get_grades()
        section_grades = course_grade[0]
        course_policy = course_grade[1]
        subsections = course_grade[2]
        assignment_type_grades = []
        grades_list = []

        for student in section_grades:
            total_section = proccess_grades_dict(student, course_policy)
            user = student['username']
            assignment_type_dict = DictList()
            course_grade_factory = CourseGradeFactory().create(user, self.course)
            for chapter, sequentials in subsections.items():
                for sequential in sequentials:
                    header_name = '{} - {}'.format(chapter, sequential.format)
                    self.headers.append(header_name)
                    weight = course_policy[sequential.format]['weight']
                    total_number = course_policy[sequential.format]['total_number']
                    calculation = (course_grade_factory.score_for_module(sequential.location)[0] * weight) / total_number
                    assignment_type_dict[header_name] = calculation

            calculated_sum = sum_dict_values(assignment_type_dict, {'username': user.username, 'fullname': user.get_full_name()})
            assignment_type_grades.append(calculated_sum)

        header_rows = proccess_headers(self.headers)

        for element in assignment_type_grades:
            ordered = order_list(header_rows, element)
            grades_list.append(ordered)

        return grades_list

    def enhanced_problem_grade(self):
        """
        Public method to generate a json report with the grades per problem.
        """
        course_grade = self.get_grades()
        section_grades = course_grade[0]
        course_policy = course_grade[1]
        rows = []
        final_grades = []
        grading_context = grading_context_for_course(self.course_key)

        for student in section_grades:
            user = student['username']
            course_grade_factory = CourseGradeFactory().create(user, self.course)
            sections = course_grade_factory.chapter_grades
            problem_score_dict = {}
            problem_score_dict['username'] = user.username
            problem_score_dict['fullname'] = user.get_full_name()

            for section in sections.items():
                chapter_name = section[1]['display_name']
                sequentials = section[1]['sections']
                # We need to walk through subsections, problem_scores and grading context
                # in order to get the type of each problem in each unit and get the
                # earneds and possibles points.
                for sequential in sequentials:
                    for problem_score in sequential.problem_scores:
                        for problem_name in grading_context['all_graded_blocks']: ## This was changed
                            if problem_name.fields['category'] == 'problem':
                                if problem_name.location.block_id == problem_score.name:
                                    grade_tuple = course_grade_factory.score_for_module(problem_name.location)
                                    header_name = '{} - {} - {}'.format(chapter_name, sequential.display_name, problem_name.fields['display_name'])
                                    new_header = [header_name + " (Earned)", header_name + " (Possible)"]
                                    problem_score_dict[new_header[0]] = grade_tuple[0]
                                    problem_score_dict[new_header[1]] = grade_tuple[1]
                                    # Since new_header is a list of two values
                                    # at the moment to append it to self.headers will build a
                                    # list of lists, and due to we need to pass a flatten list as
                                    # headers rows, we just append the 0 and 1 position item.
                                    self.headers.append(new_header[0])
                                    self.headers.append(new_header[1])

            rows.append(problem_score_dict)

        header_rows = proccess_headers(self.headers)
        # Order the rows based on the headers order.
        for element in rows:
            ordered = order_list(header_rows, element)
            final_grades.append(ordered)

        return final_grades

    def new_get_grades(self):

        all_grades_info = {}
        data = []
        for student in self.students:
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade_factory.summary
            gradeset["username"] = student.username
            gradeset["fullname"] = student.get_full_name()
            gradeset = generate_filtered_sections(gradeset)
            course_data = CourseData(student, course=self.course)
            course_policy = course_data.course.grading_policy
            gradeset = generate_by_at(gradeset, course_policy)
            data.append(gradeset)
        all_grades_info["data"] = data

        return all_grades_info

    def new_by_section(self):
        """
        Public method to generate a json report with the grades per sections.
        """
        sections_id = []
        final_grade_by_section = {}
        total_grades_by_section = []

        grades_data = self.new_get_grades()
        for student in grades_data.keys():
            for grades in grades_data[student]['section_breakdown']:
                if 'section_block_id' in grades:
                    if grades['section_block_id'] not in sections_id:
                        sections_id.append(grades['section_block_id'])

        for student in grades_data.keys():
            total_grades_by_section = []
            for section in sections_id:
                grades_by_section = []
                for grades in grades_data[student]['section_breakdown']:
                    if 'section_block_id' in grades:
                        if grades['section_block_id'] == section:
                            grades_by_section.append(grades)
                total_grades_by_section.append(get_total_grade_by_section(grades_by_section))
            final_grade_by_section[student] = total_grades_by_section
