# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-07-11 11:26
from __future__ import unicode_literals

from django.db import migrations

from openedx.core.djangoapps.system_wide_roles.constants import STUDENT_SUPPORT_ADMIN_ROLE


def create_roles(apps, schema_editor):
    """Create the system wide student support roles if they do not already exist."""
    SystemWideRole = apps.get_model('system_wide_roles', 'SystemWideRole')
    SystemWideRole.objects.update_or_create(name=STUDENT_SUPPORT_ADMIN_ROLE)


def delete_roles(apps, schema_editor):
    """Delete the system wide student support roles."""
    SystemWideRole = apps.get_model('system_wide_roles', 'SystemWideRole')
    SystemWideRole.objects.filter(
        name=STUDENT_SUPPORT_ADMIN_ROLE
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('system_wide_roles', '0001_SystemWideRole_SystemWideRoleAssignment'),
    ]

    operations = [
        migrations.RunPython(create_roles, delete_roles)
    ]
