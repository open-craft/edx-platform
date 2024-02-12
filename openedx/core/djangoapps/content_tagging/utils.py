"""
Utils functions for tagging
"""
from __future__ import annotations

from edx_django_utils.cache import RequestCache
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import LibraryLocatorV2
from organizations.models import Organization

from .types import ContentKey


def get_content_key_from_string(key_str: str) -> ContentKey:
    """
    Get content key from string
    """
    try:
        return CourseKey.from_string(key_str)
    except InvalidKeyError:
        try:
            return LibraryLocatorV2.from_string(key_str)
        except InvalidKeyError:
            try:
                return UsageKey.from_string(key_str)
            except InvalidKeyError as usage_key_error:
                raise ValueError("object_id must be a CourseKey, LibraryLocatorV2 or a UsageKey") from usage_key_error


def get_context_key_from_key_string(key_str: str) -> CourseKey | LibraryLocatorV2:
    """
    Get context key from an key string
    """
    content_key = get_content_key_from_string(key_str)
    # If the content key is a CourseKey or a LibraryLocatorV2, return it
    if isinstance(content_key, (CourseKey, LibraryLocatorV2)):
        return content_key

    # If the content key is a UsageKey, return the context key
    context_key = content_key.context_key

    if isinstance(context_key, (CourseKey, LibraryLocatorV2)):
        return context_key

    raise ValueError("context must be a CourseKey or a LibraryLocatorV2")


class TaggingRulesCache:
    """
    Caches data required for computing rules for the duration of the request.
    """

    def __init__(self):
        """
        Initializes the request cache.
        """
        self.request_cache = RequestCache('openedx.core.djangoapps.content_tagging.rules')

    def get_orgs(self, org_names: list[str] | None = None) -> list[Organization]:
        """
        Returns the Organizations with the given name(s), or all Organizations if no names given.

        Organization instances are cached for the duration of the request.
        """
        cache_key = 'all_orgs'
        all_orgs = self.request_cache.data.get(cache_key)
        if all_orgs is None:
            all_orgs = {
                org.short_name: org
                for org in Organization.objects.all()
            }
            self.request_cache.set(cache_key, all_orgs)

        if org_names:
            return [
                all_orgs[org_name] for org_name in org_names if org_name in all_orgs
            ]

        return all_orgs.values()
