"""
Tests for the create_or_update_site_configuration management command.
"""
from __future__ import absolute_import, unicode_literals

import codecs

import ddt
import yaml
from django.contrib.sites.models import Site
from django.core.management import call_command, CommandError
from django.test import TestCase
from path import Path

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration


@ddt.ddt
class CreateOrUpdateSiteConfigurationTest(TestCase):
    """
    Test for the create_or_update_site_configuration management command.
    """
    command = 'create_or_update_site_configuration'

    def setUp(self):
        super(CreateOrUpdateSiteConfigurationTest, self).setUp()
        self.site_id = 1
        self.site_id_arg = ['--site-id', str(self.site_id)]
        self.yaml_file_path = Path(__file__).parent / "fixtures/config1.yml"  # pylint: disable=old-division

    @property
    def site(self):
        """
        Return the fixture site for this test class.
        """
        return Site.objects.get(id=self.site_id)

    def assert_site_configuration_does_not_exist(self):
        """
        Assert that the site configuration for the fixture site does not exist.
        """
        with self.assertRaises(SiteConfiguration.DoesNotExist):
            SiteConfiguration.objects.get(site=self.site)

    def get_site_configuration(self):
        """
        Return the site configuration for the fixture site.
        """
        return SiteConfiguration.objects.get(site=self.site)

    def create_fixture_site_configuration(self, enabled):
        SiteConfiguration.objects.update_or_create(
            site=self.site,
            defaults={'enabled': enabled, 'values': {'ABC': 'abc', 'B': 'b'}}
        )

    def test_command_no_args(self):
        """
        Verify the error on the command with no arguments.
        """
        with self.assertRaises(CommandError) as error:
            call_command(self.command)
        self.assertIn('Error: argument --site-id is required', str(error.exception))

    def test_non_existent_site_id(self):
        """
        Verify the error when given a site ID that does not exist.
        """
        non_existent_site_id = 999
        with self.assertRaises(Site.DoesNotExist):
            Site.objects.get(id=non_existent_site_id)

        with self.assertRaises(CommandError) as error:
            call_command(self.command, '--site-id', '{}'.format(non_existent_site_id))

        self.assertIn('No site with ID {} found'.format(non_existent_site_id), str(error.exception))

    def test_site_configuration_created_when_non_existent(self):
        """
        Verify that a SiteConfiguration instance is created if it doesn't exist.
        """
        self.assert_site_configuration_does_not_exist()

        call_command(self.command, *self.site_id_arg)
        site_configuration = SiteConfiguration.objects.get(site=self.site)
        self.assertFalse(site_configuration.values)
        self.assertFalse(site_configuration.enabled)

    def test_both_enabled_disabled_flags(self):
        """
        Verify the error on providing both the --enabled and --disabled flags.
        """
        with self.assertRaises(CommandError) as error:
            call_command(self.command, '--enabled', '--disabled', *self.site_id_arg)
        self.assertIn('argument --disabled: not allowed with argument --enabled', str(error.exception))

    @ddt.data(('enabled', True),
              ('disabled', False))
    @ddt.unpack
    def test_site_configuration_enabled_disabled(self, flag, enabled):
        """
        Verify that the SiteConfiguration instance is enabled/disabled as per the flag used.
        """
        self.assert_site_configuration_does_not_exist()
        call_command(self.command, '--{}'.format(flag), *self.site_id_arg)
        site_configuration = SiteConfiguration.objects.get(site=self.site)
        self.assertFalse(site_configuration.values)
        self.assertEqual(enabled, site_configuration.enabled)

    def test_site_configuration_created_with_parameters(self):
        """
        Verify that a SiteConfiguration instance is created with the provided values if it does not exist.
        """
        self.assert_site_configuration_does_not_exist()
        call_command(self.command, '-e', 'ABC=123', '-e', 'XYZ="789"', *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        self.assertEqual(site_configuration.values, {'ABC': 123, 'XYZ': '789'})

    @ddt.data(True, False)
    def test_site_configuration_updated_with_parameters(self, enabled):
        """
        Verify that the existing parameters are updated when provided in the command.
        """
        SiteConfiguration.objects.update_or_create(
            site=self.site,
            defaults={'enabled': enabled, 'values': {'ABC': 'abc', 'B': 'b'}}
        )
        call_command(self.command, '-e', 'ABC=123', '-e', 'XYZ="789"', *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        self.assertEqual(site_configuration.values, {'ABC': 123, 'XYZ': '789', 'B': 'b'})
        self.assertEqual(site_configuration.enabled, enabled)

    @ddt.data(True, False)
    def test_site_configuration_from_yaml(self, enabled):
        """
        Verify that the existing parameteres are updated when provided through a YAML file.
        """
        self.create_fixture_site_configuration(enabled)
        call_command(self.command, '-e', '@{}'.format(self.yaml_file_path.abspath()), *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        expected_site_configuration = {'B': 'b'}
        with codecs.open(self.yaml_file_path, encoding='utf-8') as f:
            expected_site_configuration.update(yaml.safe_load(f))
        self.assertEqual(site_configuration.values, expected_site_configuration)
        self.assertEqual(site_configuration.enabled, enabled)

    def test_values_precedence_order_of_flags(self):
        """
        Verify that the overridden parameters are as per the order of the passed flags.
        """
        self.create_fixture_site_configuration(enabled=True)
        call_command(self.command, '-e', '@{}'.format(self.yaml_file_path), '-e', 'ABC=0', *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        expected_site_configuration = {'B': 'b'}
        with codecs.open(self.yaml_file_path, encoding='utf-8') as f:
            expected_site_configuration.update(yaml.safe_load(f))
        expected_site_configuration.update({'ABC': 0})
        self.assertEqual(site_configuration.values, expected_site_configuration)
