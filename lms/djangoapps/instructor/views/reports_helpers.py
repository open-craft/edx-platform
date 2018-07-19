"""
Util functions and classes to build additional reports.
"""

# -*- coding: utf-8 -*-
from __future__ import division

from datetime import datetime
from itertools import groupby
from time import time
from pytz import UTC

from django.db import transaction

from lms.djangoapps.instructor_task.tasks_helper.utils import upload_csv_to_report_store


class DictList(dict):
    """
    Modify the behavior of a dict allowing has a list of values
    when there are more than one key with the same name. For example,
    {'Key 1':[5, 9]}
    To use it just create an object with DictList(). For example, 
    new_variable = DictList()
    """
    def __setitem__(self, key, value):
        try:
            self[key]
        except KeyError:
            super(DictList, self).__setitem__(key, [])
        self[key].append(value)


def proccess_headers(headers):
    """
    Proccess duplicated values in header rows preserving the order.
    """
    seen = set()
    seen_add = seen.add
    return [item for item in headers if not (item in seen or seen_add(item))]


def proccess_grades_dict(grades_dict, course_policy):
    """
    Calculate grades taking into account the droppables for each section.
    Parameters:
        1. grades dict: Dict with the names of sections as keys and a list of dicts of each subsection (assignment type) 
           as value. For example: {'Section 1': [{'Homework': 0.15}, {'Lab': 0.35}]}
        2. course_policy: Dict with the course policy
    """
    for section, assignment_types in grades_dict.items():
        if isinstance(assignment_types, (list,)) and not section=='general_grade' and not section=='fullname':
            group_grades = []
            for assignment_type in assignment_types:
                for name, grade in assignment_type.items():
                    total_number = course_policy[name]['total_number']
                    drop = course_policy[name]['droppables']
                    average = grade / (total_number - drop)
                    group_grades.append(average)
            grades_dict.update({section: sum(group_grades)})
    return grades_dict.values()


def sum_dict_values(grades_dict, additional_items=None):
    """
    Util function to sum all values in a dict.
    Parameters:
        1. grades_dict: Dictionary with the grades of each subsection
        2. additional_items: If is neccesary add some other item to the dict.
    Caveats:
        1. Only does the sum to the values that be a list object. 
    """
    for key, value in grades_dict.items():
        if isinstance(value, (list,)):
            total = sum(value)
            if additional_items is not None:
                grades_dict.update(additional_items)
            grades_dict.update({key: total})
    return grades_dict


def order_list(sorted_list, elements):
    """
    Returns a list with the values of a dict based on a sorted list.
    Caveats:
        1. Items is sorted_list has to be present in the dict, this will be the keys.
        2. list and dict has to have the same lenght.
    Parameters:
        1. sorted_list: A list with the desired order.
        2. Dictionary
    Example:
        sorted_list = ['Item 1', 'Item 2', 'Item 3']
        elements = {'Item 2': 45, 'Item 1': 55, 'Item 3': 105}
        Wil return [55, 45, 105]
    """
    storage = []
    for header in sorted_list:
        storage.append(elements[header])
    return storage


def generate_csv(context, headers, rows, name):
    """
    Util function to generate CSV using ReportStore.
    Parameters:
        1. context: A _CourseGradeReportContext object
        2. headers: The headers for the csv
        3. rows: A list of lists with the values in the same order as headers, each list represent
           a new row in the csv.
        4. name: String for the file name.
    """
    date = datetime.now(UTC)
    context.update_status(u'Uploading grades')
    upload_csv_to_report_store([headers] + rows, name, context.course_id, date)
    return context.update_status(u'Completed grades')


def assign_grades(policy, assignment_type, chapter_name, student_grade, section_grade, sequentials):
    """
    Util function to calculate the grades and assign these calculations
    to each subsection.
    Return a DictList with the grades for each subsection of each section.
    The keys are the name of the section and the values are a list of the grades for
    each subsections.
    Parameters:
        1. policy: Dictionary with the course policy of each assignment type.
        2. assignment_type: String which represents the name of the assignment type.
        3. chapter_name: String which represents the name of the section.
        4. student_grade: Dictionary extracted from section_breakdown.
        5. section_grade: Empty DictList object.
        6. sequentials: Empty DictList object.
    Caveats
        1. It's important that section_grade be a DictList object due to a subsection,
           could have more than one assignment type with the same name, and since a dict is not
           done to have repeated keys, we need to storage their values as a list. For example we could not
           have:
           {'Homework', 0.35, 'Homework': 0, 'Lab': 0.15}
           Our custom DictList object allow us to storage them like this:
           {'Homework': [0.35, 0.35], 'Lab' [0.15]}
    """
    if policy['type'] == assignment_type:
        grade = student_grade['percent'] * policy['weight']
        sequentials[chapter_name] = student_grade['subsection']
        if not student_grade.has_key('mark'):
            section_grade[chapter_name] = {assignment_type: grade}
        else:
            # We need to assign a value when a subsection is droppabled.
            # Clearly, this value will be zero. 
            section_grade[chapter_name] = {assignment_type: 0.0}
    return section_grade


def order_by_section(graders_object):
    """
    Util function to order graders object from graders
    and return a Dicitonary ordered by section
    Parameters:
        1. graders_object: Dictionary from grade.graders.
    """
    # section_grades_to_sorted = []
    # additional_info = []
    # for grade_item in graders_object['section_breakdown']:
    #     if 'section_block_id' in grade_item:
    #         section_grades_to_sorted.append(grade_item)
    #     else:
    #         additional_info.append(grade_item)

    grades_ordered_by_section = sorted(graders_object, key=lambda x: x['section_block_id'])
    # for info_item in additional_info:
    #     grades_ordered_by_section.append(info_item)

    # graders_object['section_breakdown'] = grades_ordered_by_section
    return grades_ordered_by_section


def remove_dropped_grades(graders_object):
    """
    Util function to remove dropped graders object from graders
    and return a Dicitonary with just clean grades
    Parameters:
        1. graders_object: Dictionary from grade.graders.
    """
    if 'section_breakdown' in graders_object:
        for grade_item in graders_object['section_breakdown']:
            if ('mark' in grade_item and
                'detail' in grade_item['mark'] and
                'dropped' in grade_item['mark']['detail']):
                graders_object['section_breakdown'].remove(grade_item)

    return graders_object


def get_total_grade_by_section(graders_object):
    """
    Util function to calculate the final grade by section
    Parameters:
        1. graders_object: Dictionary from new_get_grades.
    """
    if graders_object is not None:
        final_grade = 0
        total = 0
        for item in graders_object:
             total += item['percent']
        final_grade = total / len(graders_object)

        return {
            graders_object[0]['section_display_name']: final_grade
        }

def is_grade_component(section_info):
    component = False
    is_droppable = section_info.get("mark") and "dropped" in section_info["mark"].get("detail")
    if section_info.get("section_block_id") and not is_droppable :
        component = True

    return component


def generate_filtered_sections(data):
    section_filtered = filter(is_grade_component, data["section_breakdown"])
    data["section_filtered"] = section_filtered
    return data

def generate_by_at(data, course_policy):

    section_filtered = data['section_filtered']
    section_ordered = order_by_section(section_filtered)
    section_by_at = []

    for key, section in groupby(section_ordered, lambda x: x['section_block_id']):
        list_section = list(section)
        total_by_section = sum(item['percent'] for item in list_section) / len(list_section)
        assignment_type_grades = []
        grades_per_section = {}
        for at in course_policy['GRADER']:
            filter_by_at = filter(lambda x: x['category'] == at['type'], list_section)
            if len(filter_by_at) > 0:
                total_by_at = sum(item['percent'] for item in filter_by_at if len(filter_by_at) > 0) / len(filter_by_at)
            else:
                total_by_at = 0
            at_by_section_percent = total_by_at * at['weight']
            assignment_type_grades.append({
                'type': at['type'],
                'grade': at_by_section_percent
            })
        grades_per_section = {
            'key': key,
            'at': assignment_type_grades,
            'percent': total_by_section
        }
        section_by_at.append(grades_per_section)
    data['section_by_at'] = section_by_at

    return data

class ForceNonAtomic:
    """
    Helper class to force non atomic database transactions
    """
    # pylint: disable=old-style-class, no-init, too-few-public-methods
    # pylint: disable=attribute-defined-outside-init, redefined-builtin

    def __enter__(self):
        self.before = transaction.get_connection().in_atomic_block
        transaction.get_connection().in_atomic_block = False
        return

    def __exit__(self, type, value, traceback):
        transaction.get_connection().in_atomic_block = self.before
