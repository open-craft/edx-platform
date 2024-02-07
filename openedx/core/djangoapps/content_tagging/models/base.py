"""
Content Tagging models
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import LearningContextKey, UsageKey
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
    org = models.ForeignKey(
        Organization,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        help_text=_(
            "Organization that is related to this taxonomy."
            "If None, then this taxonomy is related to all organizations."
        ),
    )
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
    def get_relationships(
        cls, taxonomy: Taxonomy, rel_type: RelType, org_short_name: str | None = None
    ) -> QuerySet:
        """
        Returns the relationships of the given rel_type and taxonomy where:
        * the relationship is available for all organizations, OR
        * (if provided) the relationship is available to the org with the given org_short_name
        """
        # A relationship with org=None means all Organizations
        org_filter = Q(org=None)
        if org_short_name is not None:
            org_filter |= Q(org__short_name=org_short_name)
        return cls.objects.filter(
            taxonomy=taxonomy,
            rel_type=rel_type,
        ).filter(org_filter)

    @classmethod
    def get_organizations(
        cls, taxonomy: Taxonomy, rel_type=RelType.OWNER,
    ) -> tuple[bool, list[Organization]]:
        """
        Returns a tuple containing:
        * bool: flag indicating whether "all organizations" have the given relationship to the taxonomy
        * orgs: list of Organizations which have the given relationship to the taxonomy
        """
        is_all_org = False
        orgs = []
        # Iterate over the taxonomyorgs instead of filtering to take advantage of prefetched data.
        for taxonomy_org in taxonomy.taxonomyorg_set.all():
            if taxonomy_org.rel_type == rel_type:
                if taxonomy_org.org is None:
                    is_all_org = True
                else:
                    orgs.append(taxonomy_org.org)

        return (is_all_org, orgs)


class ContentObjectTag(ObjectTag):
    """
    ObjectTag that requires an LearningContextKey or BlockUsageLocator as the object ID.
    """

    class Meta:
        proxy = True

    @property
    def object_key(self) -> UsageKey | LearningContextKey:
        """
        Returns the object ID parsed as a UsageKey or LearningContextKey.
        Raises InvalidKeyError object_id cannot be parse into one of those key types.

        Returns None if there's no object_id.
        """
        try:
            return LearningContextKey.from_string(self.object_id)
        except InvalidKeyError:
            return UsageKey.from_string(self.object_id)

    def clean(self):
        super().clean()
        # Make sure that object_id is a valid key
        try:
            self.object_key
        except InvalidKeyError as err:
            raise ValidationError("object_id is not a valid opaque key string.") from err
