# -*- coding: utf-8 -*-
"""
App to add custom search filter for excluding invitation-only 
and non-catalog courses
"""


from django.apps import AppConfig


class EsmeCustomSearchConfig(AppConfig):
    """
    Application configuration for CustomSearch
    """
    name = 'lms.djangoapps.esme_custom_search'
