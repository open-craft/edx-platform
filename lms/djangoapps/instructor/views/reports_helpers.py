"""
Util functions and classes to build additional reports.
"""

from __future__ import division

from datetime import datetime
from itertools import groupby
from time import time
from pytz import UTC

from django.db import transaction

from lms.djangoapps.instructor_task.tasks_helper.utils import upload_csv_to_report_store


def order_by_section_block(graders_object):
    """
    Util function to order graders object by 'section_block_id' key
    and return the same object but ordered by section
    """
    grades_ordered_by_section = sorted(graders_object, key=lambda x: x['section_block_id'])

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
    MAX_PERCENTAGE_GRADE = 1.00
    section_filtered = data['section_filtered']
    section_by_at = []
    policy = assign_at_count(data, course_policy)
    for key, section in groupby(section_filtered, lambda x: x['section_block_id']):
        list_section = list(section)
        per_assignment_types_grades = []
        grades_per_section = {}
        for at in policy['GRADER']:
            filter_by_at = filter(lambda x: x['category'] == at['type'], list_section)
            total_by_at = sum(item['percent'] for item in filter_by_at) / at['actual_count']
            max_possible_total_by_at = sum(MAX_PERCENTAGE_GRADE for item in filter_by_at) / at['actual_count']
            section_percent_by_at = total_by_at * at['weight']
            max_section_percent_by_at = max_possible_total_by_at * at['weight']
            per_assignment_types_grades.append({
                'type': at['type'],
                'grade': section_percent_by_at,
                'max_possible_grade': max_section_percent_by_at
            })
        total_by_section = sum(item['grade'] for item in per_assignment_types_grades)
        max_total_by_section = sum(item['max_possible_grade'] for item in per_assignment_types_grades)
        grades_per_section = {
            'key': key,
            'assignment_types': per_assignment_types_grades,
            'percent': total_by_section,
            'max_possible_percent': max_total_by_section,
            'section_display_name': list_section[0]['section_display_name']
        }
        section_by_at.append(grades_per_section)
    data['section_at_breakdown'] = section_by_at
    return data


def assign_at_count(data, course_policy):
    for at in course_policy['GRADER']:
        at_list = filter(lambda x: x['category'] == at['type'], data['section_filtered'])
        total_count = len(at_list)
        at.update({'actual_count': total_count})
    return course_policy


def calculate_up_to_data_grade(data, section_block_id=None):
    up_to_date_grade = 0
    if section_block_id:
        for item in data['section_at_breakdown']:
            up_to_date_grade += item['percent'] / item['max_possible_percent']
            if section_block_id == item['key']:
                data.update({'up_to_date_grade': up_to_date_grade})
                break
    else:
        data.update({'up_to_date_grade': data['percent']})
    return data


def delete_unwanted_keys(data, keys_to_delete):
    for item in keys_to_delete:
        del data[item]
    return data
