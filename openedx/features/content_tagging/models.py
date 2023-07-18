"""
Content Tagging models
"""
from django.db import models
from django.utils.translation import gettext as _
from opaque_keys import InvalidKeyError, OpaqueKey
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import LibraryLocatorV2, LibraryUsageLocatorV2
from openedx_tagging.core.tagging.models import ObjectTag, Taxonomy
from organizations.models import Organization


class TaxonomyOrg(models.Model):
    """
    Represents the many-to-many relationship between Taxonomies and Organizations.

    We keep this as a separate class from ContentTaxonomy so that class can remain a proxy for Taxonomy, keeping the
    data models and usage simple.
    """

    class RelType(models.TextChoices):
        OWNER = "OWN", _("owner")

    taxonomy = models.ForeignKey(Taxonomy, on_delete=models.CASCADE)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    rel_type = models.CharField(
        max_length=3,
        choices=RelType.choices,
        default=RelType.OWNER,
    )

    class Meta:
        indexes = [
            models.Index(fields=["taxonomy", "rel_type"]),
            models.Index(fields=["taxonomy", "rel_type", "org"]),
        ]

    @classmethod
    def get_owners(
        cls,
        taxonomy: Taxonomy,
    ) -> models.QuerySet:
        """
        Returns the org "owners" on the given taxonomy.

        If the returned list is empty, then the returned taxonomy is enabled for all organizations.
        """
        return cls.objects.filter(
            taxonomy=taxonomy,
            rel_type=cls.RelType.OWNER,
        )

    @classmethod
    def is_owner(cls, taxonomy: Taxonomy, org_short_name: str) -> bool:
        """
        Returns True if there's an "owner" relationship between the given taxonomy and an org with the given short name.

        Or, if no "owner" relationships exist for the given taxonomy, then all orgs are enabled for that taxonomy.
        """
        org_owners = cls.get_owners(taxonomy)
        if not org_owners.exists():
            return True
        org_owners = org_owners.filter(org__short_name=org_short_name)
        return org_owners.exists()


class ContentTag(ObjectTag):
    """
    ObjectTag that requires an opaque key as an object ID.
    """

    class Meta:
        proxy = True

    OPAQUE_KEY_TYPES = [
        UsageKey,
        CourseKey,
        LibraryLocatorV2,
        LibraryUsageLocatorV2,
    ]

    @property
    def object_key(self) -> OpaqueKey:
        """
        Returns the object ID parsed as an Opaque Key, or None if invalid.
        """
        if self.object_id:
            for OpaqueKeyClass in (UsageKey, CourseKey):
                try:
                    return OpaqueKeyClass.from_string(str(self.object_id))
                except InvalidKeyError:
                    pass
        return None


class ContentTaxonomy(Taxonomy):
    """
    Taxonomy that accepts ContentTags,
    and ensures a valid TaxonomyOrg owner relationship with the content object.
    """

    class Meta:
        proxy = True

    def _check_object(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if this ObjectTag has a valid object_id.
        """
        content_tag = ContentTag.cast(object_tag)
        return super()._check_object(content_tag) and content_tag.object_key

    def _check_taxonomy(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if this taxonomy is owned by the tag's org.
        """
        object_key = ContentTag.cast(object_tag).object_key
        return (
            super()._check_taxonomy(object_tag)
            and object_key
            and TaxonomyOrg.is_owner(self, object_key.org)
        )
