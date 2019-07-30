"""
Discount API URLs
"""
from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import url

from .views import CourseUserDiscount

urlpatterns = [
    url(r'^course/{}'.format(settings.COURSE_KEY_PATTERN), CourseUserDiscount.as_view(), name='course_user_discount'),
]
