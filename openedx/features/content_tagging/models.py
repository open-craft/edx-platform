"""
Content Tagging models
"""
from django.db import models
from django.utils.translation import gettext as _
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx_tagging.core.tagging.models import ClosedObjectTag, OpenObjectTag, Taxonomy
from openedx_tagging.core.tagging.registry import register_object_tag_class
from organizations.models import Organization


class TaxonomyOrg(models.Model):
    """
    Represents the many-to-many relationship between Taxonomies and Organizations.
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


class OrgObjectTagMixin:
    """
    Mixin for ObjectTag that checks the TaxonomyOrg owner relationship.
    """

    @property
    def org_short_name(self):
        """
        Subclasses should override this to return the object tag's org short name.
        """
        raise NotImplementedError

    def _check_taxonomy(self):
        """
        Returns True if this ObjectTag's taxonomy is owned by the org.
        """
        if not super()._check_taxonomy():
            return False

        if not TaxonomyOrg.is_owner(self.taxonomy, self.org_short_name):
            return False

        return True


class BlockObjectTagMixin:
    """
    Checks that the object_id is a valid opaque key.
    """

    OBJECT_KEY_CLASS = UsageKey

    @property
    def object_key(self):
        """
        Returns the object ID parsed as an Opaque Key, or None if invalid.
        """
        if self.object_id:
            try:
                return self.OBJECT_KEY_CLASS.from_string(str(self.object_id))
            except InvalidKeyError:
                pass
        return None

    @property
    def org_short_name(self):
        """
        Returns the org short name, if one can be parsed from the object ID.
        """
        object_key = self.object_key
        if object_key:
            return object_key.org
        return None

    def _check_object(self):
        """
        Returns True if this ObjectTag has a valid object_key.
        """
        if not self.object_key:
            return False

        return super()._check_object()


class CourseObjectTagMixin(BlockObjectTagMixin):
    """
    Mixin for ObjectTag that accepts course keys as object IDs.
    """

    OBJECT_KEY_CLASS = CourseKey


class OpenCourseObjectTag(CourseObjectTagMixin, OpenObjectTag):
    """
    CourseObjectTag for use with free-text taxonomies.
    """


class ClosedCourseObjectTag(CourseObjectTagMixin, ClosedObjectTag):
    """
    CourseObjectTag for use with closed taxonomies.
    """


class OpenBlockObjectTag(BlockObjectTagMixin, OpenObjectTag):
    """
    BlockObjectTag for use with free-text taxonomies.
    """


class ClosedBlockObjectTag(BlockObjectTagMixin, ClosedObjectTag):
    """
    BlockObjectTag for use with closed taxonomies.
    """


# Register the object tag classes in reverse order for how we want them considered
register_object_tag_class(OpenCourseObjectTag)
register_object_tag_class(OpenBlockObjectTag)
register_object_tag_class(ClosedCourseObjectTag)
register_object_tag_class(ClosedBlockObjectTag)
