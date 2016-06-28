# -*- coding: utf-8 -*-
"""
Management commands for third_party_auth
"""
from django.core.management.base import BaseCommand, CommandError
import logging
from third_party_auth.models import SAMLConfiguration
from third_party_auth.tasks import fetch_saml_metadata, sync_cloudera_accounts


class Command(BaseCommand):
    """ manage.py commands to manage SAML/Shibboleth SSO """
    help = '''Configure/maintain/update SAML-based SSO'''

    #def add_arguments(self, parser):
    #    parser.add_argument('--syncclouderaaccounts', action='store_true', help="Sync cloudera accounts")

    def handle(self, *args, **options):
        # if not SAMLConfiguration.is_enabled():
        #     raise CommandError("SAML support is disabled via SAMLConfiguration.")
	
	subcommand = args[0]
	
        if subcommand == "syncclouderaaccounts":
            log_handler = logging.StreamHandler(self.stdout)
            log_handler.setLevel(logging.DEBUG)
            log = logging.getLogger('third_party_auth.tasks')
            log.propagate = False
            log.addHandler(log_handler)
            result, count, users_sync = sync_cloudera_accounts()
	    self.stdout.write(
                "\nResult: {result}. {count} was syncronized. User list:\n{users_sync}".format(
                    result=result, count=count, users_sync='\n'.join(users_sync)
                )
            )
        else:
            raise CommandError("Unknown argment: {}".format(subcommand))

