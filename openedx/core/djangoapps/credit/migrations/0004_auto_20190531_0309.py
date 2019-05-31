# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credit', '0003_auto_20160511_2227'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='creditrequirementstatus',
            options={'verbose_name_plural': '\u05de\u05e6\u05d1\u05d9 \u05d3\u05e8\u05d9\u05e9\u05d5\u05ea \u05dc\u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d6\u05db\u05d5\u05ea'},
        ),
        migrations.AlterField(
            model_name='creditconfig',
            name='cache_ttl',
            field=models.PositiveIntegerField(default=0, help_text='\u05de\u05e6\u05d5\u05d9\u05df \u05d1\u05e9\u05e0\u05d9\u05d5\u05ea. \u05d0\u05e4\u05e9\u05e8 \u05d0\u05d7\u05e1\u05d5\u05df \u05d1\u05de\u05d8\u05de\u05d5\u05df \u05e2\u05dc \u05d9\u05d3\u05d9 \u05d4\u05d2\u05d3\u05e8\u05ea \u05d4\u05e2\u05e8\u05da \u05dc\u05d2\u05d3\u05d5\u05dc \u05de-0.', verbose_name='\u05d6\u05de\u05df \u05d7\u05d9\u05d9\u05dd \u05dc\u05de\u05d8\u05de\u05d5\u05df'),
        ),
    ]
