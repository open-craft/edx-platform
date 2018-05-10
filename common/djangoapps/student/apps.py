"""
Configuration for the ``student`` Django application.
"""
from __future__ import absolute_import
from waffle import switch_is_active

from django.apps import AppConfig
from django.contrib.admin import site as admin_site
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save


class StudentConfig(AppConfig):
    """
    Default configuration for the ``student`` application.
    """
    name = 'student'

    def ready(self):
        from django.contrib.auth.models import update_last_login as django_update_last_login
        user_logged_in.disconnect(django_update_last_login)
        from .signals.receivers import update_last_login
        user_logged_in.connect(update_last_login)

        from django.contrib.auth.models import User
        from .signals.receivers import on_user_updated
        pre_save.connect(on_user_updated, sender=User)

        # CourseEnrollmentAdmin disabled for performance reasons, see
        # https://openedx.atlassian.net/browse/OPS-2943
        # Note: for changes to this waffle flag to take effect, a service restart is required.
        if switch_is_active('enable_course_enrollment_admin'):
            from .models import CourseEnrollment
            from .admin import CourseEnrollmentAdmin
            admin_site.register(CourseEnrollment, admin_class=CourseEnrollmentAdmin)
