import logging

import ddt
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models.base import ModelBase
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.config_model_utils.models import \
    CourseAppConfigOptionsModel
from openedx.core.djangoapps.site_configuration.tests.factories import SiteFactory

log = logging.getLogger(__name__)


@ddt.ddt
class CourseAppConfigurationModelTest(TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a real model from the mixin
        cls.model = ModelBase(
            "Test" + CourseAppConfigOptionsModel.__name__,
            (CourseAppConfigOptionsModel,),
            {'__module__': CourseAppConfigOptionsModel.__module__}
        )

        # Use schema_editor to create schema
        with connection.schema_editor() as editor:
            editor.create_model(cls.model)

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        # allow the transaction to exit
        super().tearDownClass()

        # Use schema_editor to delete schema
        with connection.schema_editor() as editor:
            editor.delete_model(cls.model)

        # close the connection
        connection.close()

    def make_config_object(self, site=None, org=None, org_course=None, context_key=None, slug=None, enabled=True):
        if isinstance(site, str):
            site = SiteFactory.create(name=site)
        if slug is None:
            slug = 'site:{}-org:{}-org_course:{}-context:{}-enabled:{}'.format(
                site,
                org,
                org_course,
                context_key,
                enabled,
            )
        return self.model.objects.create(
            site=site,
            org=org,
            org_course=org_course,
            context_key=context_key,
            slug=slug,
            enabled=enabled,
        )

    def setUp(self):
        self.site1 = Site.objects.get(id=settings.SITE_ID)
        self.site2 = SiteFactory.create()
        self.org1 = 'TestOrg1'
        self.org2 = 'TestOrg2'
        self.course = 'toy'
        self.run = 'config_test'
        self.org1_course_run = CourseKey.from_string('course-v1:{}+{}+{}'.format(self.org1, self.course, self.run))
        self.org1_course = '{}+{}'.format(
            self.org1,
            self.course,
        )
        # Set up configurations at multiple levels
        self.make_config_object(site=self.site1, slug="config-1")
        self.make_config_object(site=self.site2, slug="config-2")
        self.make_config_object(site=self.site1, enabled=False, slug="config-3")
        self.make_config_object(org=self.org1, slug="config-4")
        self.make_config_object(org_course=self.org1_course, slug="config-5")
        self.make_config_object(context_key=self.org1_course_run, slug="config-6")

    def test_disallow_multiple_levels(self):
        with self.assertRaises(ValidationError) as context:
            self.model.objects.create(
                org="Test",
                org_course="Test/Course",
            ).clean()

        self.assertEqual(
            context.exception.message,
            "Configuration may not be specified at more than one level at once."
        )

    def test_disallow_slug_reuse_across_levels(self):
        self.model.objects.create(org="Test", slug="test-slug").clean()

        with self.assertRaises(ValidationError) as context:
            self.model.objects.create(site=SiteFactory.create(), slug="test-slug").clean()

        self.assertEqual(
            context.exception.message,
            "This configuration slug is already used by another configuration."
        )

        with self.assertRaises(ValidationError) as context:
            self.model.objects.create(org="Test2", slug="test-slug").clean()

        self.assertEqual(
            context.exception.message,
            "This configuration slug is already used by another configuration."
        )

        with self.assertRaises(ValidationError) as context:
            self.model.objects.create(org_course="Test+Course", slug="test-slug").clean()

        self.assertEqual(
            context.exception.message,
            "This configuration slug is already used by another configuration."
        )

    def test_allow_same_slug_at_same_level(self):
        self.make_config_object(org=self.org1, slug="test-slug").clean()
        self.make_config_object(org=self.org1, slug="test-slug").clean()

        self.make_config_object(org_course=self.org1_course, slug="test-course-slug").clean()
        self.make_config_object(org_course=self.org1_course, slug="test-course-slug").clean()

    def test_get_current(self):
        config1 = self.make_config_object(org=self.org1, slug="test-slug")
        config2 = self.make_config_object(org=self.org1, slug="test-slug")
        # config2 should override config1.
        self.assertNotEqual(self.model.current(context_key=self.org1_course_run, slug="test-slug"), config1)
        self.assertEqual(self.model.current(context_key=self.org1_course_run, slug="test-slug"), config2)
        config2_id = config2.id
        config2.save()
        # The current model should not have the same id as the old config2 since saving generates a new id
        # and doesn't modify the existing object
        self.assertNotEqual(self.model.current(context_key=self.org1_course_run, slug="test-slug").id, config2_id)

    @ddt.data(
        # site, org, org_course, context_key, slug_keys
        (1, None, None, None, [1]),
        (2, None, None, None, [2]),
        (None, 'TestOrg1', None, None, [1, 4]),
        (None, None, 'TestOrg1+SomeCourse', None, [1, 4]),
        (None, None, None, 'course-v1:TestOrg1+Course+run', [1, 4]),
        (None, None, 'TestOrg1+toy', None, [1, 4, 5]),
        (None, None, None, 'course-v1:TestOrg1+Course+run', [1, 4]),
        (None, None, None, 'course-v1:TestOrg1+toy+run', [1, 4, 5]),
        (None, None, None, 'course-v1:TestOrg1+toy+config_test', [1, 4, 5, 6]),
        (None, 'TestOrg2', None, None, [1]),
    )
    @ddt.unpack
    def test_available_options(self, site, org, org_course, context_key, slug_keys):
        if context_key:
            context_key = CourseKey.from_string(context_key)
        if site:
            site = Site.objects.get(id=site)
        available_config_slugs = list(
            self.model.available(
                site=site,
                org=org,
                org_course=org_course,
                context_key=context_key,
            ).values_list('slug', flat=True)
        )
        self.assertEqual(len(available_config_slugs), len(slug_keys))
        for config_slug_key in slug_keys:
            self.assertIn('config-{}'.format(config_slug_key), available_config_slugs)
