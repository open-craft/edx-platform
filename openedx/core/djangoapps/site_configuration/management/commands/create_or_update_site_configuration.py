"""Create or updates the SiteConfiguration for a site. """

from __future__ import unicode_literals

import codecs
import json
import re

import yaml

from django.contrib.sites.models import Site
from django.core.management import BaseCommand, CommandError


from openedx.core.djangoapps.site_configuration.models import SiteConfiguration


class Command(BaseCommand):
    """Management command to create or update SiteConfiguration."""
    help = 'Create or update SiteConfiguration'

    def add_arguments(self, parser):
        parser.add_argument('--site-id',
                            action='store',
                            dest='site_id',
                            type=int,
                            required=True,
                            help='ID of the Site whose SiteConfiguration has to be updated.')
        parser.add_argument('-e', '--extra-vars',
                            action='append',
                            dest='extra_vars',
                            help='Set or update additional SiteConfiguration parameters as KEY=VALUE '
                                 'or YAML if filename prepended with @.')

        group = parser.add_mutually_exclusive_group()
        group.add_argument('--enabled',
                           action='store_true',
                           dest='enabled',
                           default=None,
                           help='Enable the SiteConfiguration.')
        group.add_argument('--disabled',
                           action='store_false',
                           dest='enabled',
                           help='Disable the SiteConfiguration.')

    def handle(self, *args, **options):
        site_id = options.get('site_id')
        extra_vars = options.get('extra_vars')
        enabled = options.get('enabled')

        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            raise CommandError('No site with ID {} found'.format(site_id))

        site_configuration_values = {}

        if extra_vars:
            for extra_var in extra_vars:
                var = extra_var.strip()
                if var.startswith('@'):
                    with codecs.open(var[1:], encoding='utf-8') as f:
                        site_configuration_values.update(yaml.safe_load(f))
                else:
                    tokens = var.split('=')
                    if len(tokens) != 2:
                        raise CommandError('Invalid format for the --extra-vars parameter. '
                                           'Expected: KEY=VALUE, quoted as appropriate.')
                    key, value = tokens
                    key_regex = re.compile('[a-zA-Z][a-zA-Z0-9-_]*')
                    if not key_regex.match(key):
                        raise CommandError("Invalid key '{}' provided in the --extra-vars parameter".format(key))
                    site_configuration_values[key] = json.loads(value)

        site_configuration_defaults = {
            'values': site_configuration_values
        }
        site_configuration, created = SiteConfiguration.objects.get_or_create(site=site)

        if site_configuration.values:
            site_configuration.values.update(site_configuration_values)
        else:
            site_configuration.values = site_configuration_values

        if enabled is not None:
            site_configuration.enabled = enabled

        site_configuration.save()
