# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('course_creators', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursecreator',
            name='note',
            field=models.CharField(help_text='\u05d4\u05e2\u05e8\u05d5\u05ea \u05d0\u05d5\u05e4\u05e6\u05d9\u05d5\u05e0\u05dc\u05d9\u05d5\u05ea \u05d0\u05d5\u05d3\u05d5\u05ea \u05de\u05e9\u05ea\u05de\u05e9 \u05d6\u05d4 (\u05dc\u05d3\u05d5\u05d2\u05de\u05d4, \u05de\u05d3\u05d5\u05e2 \u05e0\u05e9\u05dc\u05dc\u05d4 \u05d2\u05d9\u05e9\u05d4 \u05dc\u05d9\u05e6\u05d9\u05e8\u05ea \u05e7\u05d5\u05e8\u05e1)', max_length=512, blank=True),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='state',
            field=models.CharField(default=b'unrequested', help_text='\u05de\u05e6\u05d1 \u05e0\u05d5\u05db\u05d7\u05d9 \u05e9\u05dc \u05d9\u05d5\u05e6\u05e8 \u05d4\u05e7\u05d5\u05e8\u05e1', max_length=24, choices=[(b'unrequested', '\u05dc\u05d0 \u05e0\u05d3\u05e8\u05e9'), (b'pending', '\u05de\u05de\u05ea\u05d9\u05df \u05dc\u05d0\u05d9\u05e9\u05d5\u05e8'), (b'granted', '\u05d0\u05d5\u05e9\u05e8'), (b'denied', '\u05e0\u05e9\u05dc\u05dc')]),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='state_changed',
            field=models.DateTimeField(help_text='\u05d4\u05ea\u05d0\u05e8\u05d9\u05da \u05e9\u05d1\u05d5 \u05e2\u05d5\u05d3\u05db\u05df \u05dc\u05d0\u05d7\u05e8\u05d5\u05e0\u05d4 \u05d4\u05de\u05e6\u05d1', verbose_name=b'state last updated', auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, help_text='\u05de\u05e9\u05ea\u05de\u05e9 \u05e1\u05d8\u05d5\u05d3\u05d9\u05d5'),
        ),
    ]
