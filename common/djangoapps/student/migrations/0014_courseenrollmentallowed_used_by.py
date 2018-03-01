# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

# FIXME delete
# def migrate_data_forwards(apps, schema_editor):
#     CourseEnrollmentAllowed = apps.get_model('student', 'CourseEnrollmentAllowed')
#     # link all CEAs that have a CourseEnrollment
#     for cea in CourseEnrollmentAllowed.objects.all():
#         … 
#         # if there's an enrollment, …
# 
# 
# def migrate_data_backwards(apps, schema_editor):
#     raise NotImplementedError()

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('student', '0013_delete_historical_enrollment_records'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseenrollmentallowed',
            name='used_by',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text="First user which enrolled in the specified course through the specified e-mail. Once set, it won't change.", null=True),
        ),
    ]
