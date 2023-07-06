"""
Content Tagging APIs
"""
from typing import Generator, List, Type

import openedx_tagging.core.tagging.api as oel_tagging
from openedx_tagging.core.tagging.models import Taxonomy
from organizations.models import Organization

from .models import TaxonomyOrg


def create_taxonomy(
    name: str,
    org_owners: List[Organization] = None,
    description: str = None,
    enabled=True,
    required=False,
    allow_multiple=False,
    allow_free_text=False,
    system_defined=False,
    object_tag_class: Type = None,
) -> Taxonomy:
    """
    Creates, saves, and returns a new Taxonomy with the given attributes.

    If `org_owners` is empty/None, then the returned taxonomy is enabled for all organizations.
    """
    taxonomy = oel_tagging.create_taxonomy(
        name=name,
        description=description,
        enabled=enabled,
        required=required,
        allow_multiple=allow_multiple,
        allow_free_text=allow_free_text,
        system_defined=system_defined,
        object_tag_class=object_tag_class,
    )
    if org_owners:
        set_taxonomy_org_owners(taxonomy, org_owners)
    return taxonomy


def set_taxonomy_org_owners(
    taxonomy: Taxonomy,
    org_owners: List[Organization] = None,
):
    """
    Updates the list of org "owners" on the given taxonomy.

    If `org_owners` is empty/None, then the taxonomy is enabled for all organizations.
    """
    TaxonomyOrg.get_owners(taxonomy).delete()
    if org_owners:
        TaxonomyOrg.objects.bulk_create(
            [
                TaxonomyOrg(
                    taxonomy=taxonomy,
                    org=org,
                    rel_type=TaxonomyOrg.RelType.OWNER,
                )
                for org in org_owners
            ]
        )


def get_taxonomies_for_org(
    org_owner: Organization = None, enabled=True
) -> Generator[Taxonomy, None, None]:
    """
    Generates a list of the enabled Taxonomies owned by the given org, sorted by name.

    If you want the disabled Taxonomies, pass enabled=False.
    If you want all Taxonomies (both enabled and disabled), pass enabled=None.
    """
    taxonomies = oel_tagging.get_taxonomies(enabled=enabled)
    for taxonomy in taxonomies.all():
        org_short_name = org_owner.short_name if org_owner else None
        if TaxonomyOrg.is_owner(taxonomy, org_short_name):
            yield taxonomy


# Expose the oel_tagging APIs

get_taxonomy = oel_tagging.get_taxonomy
get_taxonomies = oel_tagging.get_taxonomies
get_tags = oel_tagging.get_tags
cast_object_tag = oel_tagging.cast_object_tag
resync_object_tags = oel_tagging.resync_object_tags
get_object_tags = oel_tagging.get_object_tags
tag_object = oel_tagging.tag_object
