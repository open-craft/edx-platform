"""
Cohort API URLs
"""

from django.conf import settings
from django.conf.urls import url

from . import api

urlpatterns = [
    url(
        r'^v1/{}/settings$'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.course_cohort_settings_handler,
        name='api_cohort_settings',
    ),
    url(
        r'^v1/{}/(?P<cohort_id>[0-9]+)?$'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.cohort_handler,
        name='api_cohorts',
    ),
    url(
        r'^v1/{}/(?P<cohort_id>[0-9]+)$'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.users_in_cohort,
        name='api_list_cohort',
    ),
    url(
        r'^v1/{}/(?P<cohort_id>[0-9]+)/add$'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.add_users_to_cohort,
        name='api_add_to_cohort',
    ),
    url(
        r'^v1/{}/(?P<cohort_id>[0-9]+)/delete$'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.remove_user_from_cohort,
        name='api_remove_from_cohort',
    ),
    url(
        r'^v1/{}/add_users_to_cohort'.format(
            settings.COURSE_KEY_PATTERN,
        ),
        api.add_users_from_csv,
        name='api_add_users_csv',
    ),
]
