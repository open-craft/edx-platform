"""
Content Tagging APIs
"""
from typing import Generator, List, Type

import openedx_tagging.core.tagging.api as oel_tagging
from openedx_tagging.core.tagging.models import ObjectTag, Taxonomy
from organizations.models import Organization

from .models import BlockObjectTag, CourseObjectTag, TaxonomyOrg


def create_taxonomy(
    name: str,
    org_owners: List[Organization] = None,
    description: str = None,
    enabled=True,
    required=False,
    allow_multiple=False,
    allow_free_text=False,
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


def tag_object(
    taxonomy: Taxonomy, tags: List, object_id: str, object_type: str, object_tag_class: Type=None,
) -> List[ObjectTag]:
    """
    Replaces the existing ObjectTag entries for the given taxonomy + object_id with the given list of tags.

    If taxonomy.allows_free_text, then the list should be a list of tag values.
    Otherwise, it should be a list of existing Tag IDs.

    Raised ValueError if the proposed tags are invalid for this taxonomy.
    Preserves existing (valid) tags, adds new (valid) tags, and removes omitted (or invalid) tags.

    Sets the object_tag_class based on the given ``object_type``.
    """
    if not object_tag_class:
        if object_type == 'block':
            object_tag_class = BlockObjectTag
        elif object_type == 'course':
            object_tag_class = CourseObjectTag
    return oel_tagging.tag_object(
        taxonomy=taxonomy,
        tags=tags,
        object_id=object_id,
        object_type=object_type,
        object_tag_class=object_tag_class,
    )


# Expose the oel_tagging APIs

get_taxonomy = oel_tagging.get_taxonomy
get_taxonomies = oel_tagging.get_taxonomies
get_tags = oel_tagging.get_tags
cast_object_tag = oel_tagging.cast_object_tag
resync_object_tags = oel_tagging.resync_object_tags
get_object_tags = oel_tagging.get_object_tags
