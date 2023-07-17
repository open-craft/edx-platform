# Generated by Django 3.2.20 on 2023-07-17 07:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("oel_tagging", "__latest__"),
        ("organizations", "0003_historicalorganizationcourse"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlockObjectTag",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("oel_tagging.objecttag",),
        ),
        migrations.CreateModel(
            name="TaxonomyOrg",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rel_type",
                    models.CharField(
                        choices=[("OWN", "owner")], default="OWN", max_length=3
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organizations.organization",
                    ),
                ),
                (
                    "taxonomy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="oel_tagging.taxonomy",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CourseObjectTag",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("content_tagging.blockobjecttag",),
        ),
        migrations.AddIndex(
            model_name="taxonomyorg",
            index=models.Index(
                fields=["taxonomy", "rel_type"], name="content_tag_taxonom_b04dd1_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="taxonomyorg",
            index=models.Index(
                fields=["taxonomy", "rel_type", "org"],
                name="content_tag_taxonom_70d60b_idx",
            ),
        ),
    ]
