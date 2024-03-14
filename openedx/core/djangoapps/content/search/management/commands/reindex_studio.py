"""
Command to build or re-build the search index for courses (in Studio, i.e. Draft
mode), in Meilisearch.

See also cms/djangoapps/contentstore/management/commands/reindex_course.py which
indexes LMS (published) courses in ElasticSearch.
"""
from django.core.management import BaseCommand

from ... import api


class Command(BaseCommand):
    """
    Build or re-build the search index for courses (in Studio, i.e. Draft mode)
    """

    def handle(self, *args, **options):
        """
        Build a new search index for Studio, containing content from courses and libraries
        """
        api.rebuild_index(self.stdout.write)
