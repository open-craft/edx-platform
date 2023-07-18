"""
Content Tagging APIs
"""
from typing import Iterator, List, Type

import openedx_tagging.core.tagging.api as oel_tagging
from openedx_tagging.core.tagging.models import Taxonomy
from organizations.models import Organization

from .models import ContentTag, ContentTaxonomy, TaxonomyOrg


def create_taxonomy(
    name: str,
    org_owners: List[Organization] = None,
    description: str = None,
    enabled=True,
    required=False,
    allow_multiple=False,
    allow_free_text=False,
    taxonomy_class: Type = ContentTaxonomy,
) -> Taxonomy:
    """
    Creates, saves, and returns a new Taxonomy with the given attributes.

    If `taxonomy_class` not provided, then uses ContentTaxonomy.

    If `org_owners` is empty/None, then the returned taxonomy is enabled for all organizations.
    """
    taxonomy = oel_tagging.create_taxonomy(
        name=name,
        description=description,
        enabled=enabled,
        required=required,
        allow_multiple=allow_multiple,
        allow_free_text=allow_free_text,
        taxonomy_class=taxonomy_class,
    ).cast()
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
) -> Iterator[Taxonomy]:
    """
    Generates a list of the enabled Taxonomies owned by the given org, sorted by name.

    If you want the disabled Taxonomies, pass enabled=False.
    If you want all Taxonomies (both enabled and disabled), pass enabled=None.
    """
    taxonomies = oel_tagging.get_taxonomies(enabled=enabled)
    for taxonomy in taxonomies.all():
        org_short_name = org_owner.short_name if org_owner else None
        if TaxonomyOrg.is_owner(taxonomy, org_short_name):
            yield taxonomy.cast()


def get_object_tags(
    object_id: str, taxonomy: Taxonomy = None, valid_only=True
) -> Iterator[ContentTag]:
    """
    Generates a list of content tags for a given object.

    Pass taxonomy to limit the returned object_tags to a specific taxonomy.

    Pass valid_only=False when displaying tags to content authors, so they can see invalid tags too.
    Invalid tags will (probably) be hidden from learners.
    """
    for object_tag in oel_tagging.get_object_tags(
        object_id=object_id,
        taxonomy=taxonomy,
        valid_only=valid_only,
    ):
        yield ContentTag.cast(object_tag)


def tag_object(
    taxonomy: Taxonomy,
    tags: List,
    object_id: str,
) -> List[ContentTag]:
    """
    Replace the existing ObjectTag entries for the given taxonomy + object_id with the given list of tags.

    If taxonomy.allows_free_text, then the list should be a list of tag values.
    Otherwise, it should be a list of existing Tag IDs.

    Raises ValueError if the proposed tags are invalid for this taxonomy.
    Preserves existing (valid) tags, adds new (valid) tags, and removes omitted (or invalid) tags.
    """
    # Check that this will create valid ContentTags
    content_tag = ContentTag(object_id=object_id)
    if not content_tag.object_key:
        raise ValueError(f"Invalid ContentTag.object_id: {object_id}")
    content_tags = []
    for object_tag in oel_tagging.tag_object(
        taxonomy=taxonomy,
        tags=tags,
        object_id=object_id,
    ):
        content_tags.append(ContentTag.cast(object_tag))
    return content_tags


# Expose the oel_tagging APIs

get_taxonomy = oel_tagging.get_taxonomy
get_taxonomies = oel_tagging.get_taxonomies
get_tags = oel_tagging.get_tags
resync_object_tags = oel_tagging.resync_object_tags
