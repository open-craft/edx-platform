"""
keyword_substitution.py

Contains utility functions to help substitute keywords in a text body with
the appropriate user / course data.

Supported:
    LMS:
        - %%USER_ID%% => anonymous user id
        - %%USER_FULLNAME%% => User's full name
        - %%COURSE_ID%% => display HTML ID of the course
        - %%COURSE_DISPLAY_NAME%% => display name of the course
        - %%COURSE_END_DATE%% => end date of the course

Usage:
    Call substitute_keywords_with_data where substitution is
    needed. Currently called in:
        - LMS: Announcements + Bulk emails
        - CMS: Not called
"""

from django.contrib.auth.models import User

from student.models import anonymous_id_for_user


def anonymous_id_from_user_id(user_id):
    """
    Gets a user's anonymous id from their user id
    """
    user = User.objects.get(id=user_id)
    return anonymous_id_for_user(user, None)


def substitute_keywords(string, user_id, context):
    """
    Replaces all %%-encoded words using KEYWORD_FUNCTION_MAP mapping functions

    Iterates through all keywords that must be substituted and replaces
    them by calling the corresponding functions stored in KEYWORD_FUNCTION_MAP.

    Functions stored in KEYWORD_FUNCTION_MAP must return a replacement string.
    """

    # do this lazily to avoid unneeded database hits
    KEYWORD_FUNCTION_MAP = {
        '%%USER_ID%%': lambda: anonymous_id_from_user_id(user_id),
        '%%USER_FULLNAME%%': lambda: context.get('name'),
        '%%COURSE_ID%%': lambda: context.course_id.html_id(),
        '%%COURSE_DISPLAY_NAME%%': lambda: context.get('course_title'),
        '%%COURSE_END_DATE%%': lambda: context.get('course_end_date'),
    }

    for key in KEYWORD_FUNCTION_MAP.keys():
        if key in string:
            try:
                substitutor = KEYWORD_FUNCTION_MAP[key]
                string = string.replace(key, substitutor())
            except (KeyError, AttributeError, TypeError):
                # Do not replace the keyword when substitutor is not present.
                pass

    return string


def substitute_keywords_with_data(string, context):
    """
    Given an email context, replaces all %%-encoded words in the given string
    `context` is a dictionary that should include `user_id` and `course_title`
    keys
    """

    # Do not proceed without parameters: Compatibility check with existing tests
    # that do not supply these parameters
    user_id = context.get('user_id') or getattr(context, 'user_id')
    course_title = context.get('course_title') or getattr(context, 'course_id')

    if None in (string, user_id, course_title):
        return string

    return substitute_keywords(string, user_id, context)
