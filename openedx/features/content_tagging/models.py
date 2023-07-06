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


class CourseObjectTagMixin:
    """
    Mixin for ObjectTag that accepts course keys as object IDs.
    """

    @classmethod
    def valid_for(cls, object_id: str = None, **kwargs) -> bool:
        """
        Returns True if the given object_id is a valid CourseKey.
        """
        if not object_id:
            return False

        try:
            CourseKey.from_string(object_id)
            return True
        except InvalidKeyError:
            return False

    def _check_object(self):
        """
        Returns True if this CourseObjectTag has a valid course key.
        """
        try:
            course_key = CourseKey.from_string(self.object_id)
        except InvalidKeyError:
            return False

        # ...and the course must use an org that's enabled for this taxonomy.
        if not TaxonomyOrg.is_owner(self.taxonomy, course_key.org):
            return False

        return True


class BlockObjectTagMixin:
    """
    Mixin for ObjectTag that accepts usage keys as object IDs.
    """

    @classmethod
    def valid_for(cls, object_id: str = None, **kwargs) -> bool:
        """
        Returns True if the given object_id is a valid UsageKey.
        """
        if not object_id:
            return False

        try:
            UsageKey.from_string(object_id)
            return True
        except InvalidKeyError:
            return False

    def _check_object(self):
        """
        Returns True if this BlockObjectTag has a valid usage key,
        and an org that's enabled for its taxonomy.
        """
        try:
            usage_key = UsageKey.from_string(self.object_id)
        except InvalidKeyError:
            return False

        # ...and the course must use an org that's enabled for this taxonomy.
        if not TaxonomyOrg.is_owner(self.taxonomy, usage_key.org):
            return False

        return True


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
