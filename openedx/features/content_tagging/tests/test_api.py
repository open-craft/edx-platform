"""Tests for the Tagging models"""
import ddt
from django.test.testcases import TestCase
from openedx_tagging.core.tagging.models import ObjectTag, Tag
from organizations.models import Organization

from .. import api


class TestTaxonomyMixin:
    """
    Sets up data for testing Content Taxonomies.
    """

    def setUp(self):
        super().setUp()
        self.org1 = Organization.objects.create(name="OpenedX", short_name="OeX")
        self.org2 = Organization.objects.create(name="Axim", short_name="Ax")
        # Taxonomies
        self.taxonomy_disabled = api.create_taxonomy(
            name="Learning Objectives",
            enabled=False,
        )
        self.taxonomy_all_orgs = api.create_taxonomy(
            name="Content Types",
            enabled=True,
        )
        self.taxonomy_both_orgs = api.create_taxonomy(
            name="OpenedX/Axim Content Types",
            enabled=True,
            org_owners=[self.org1, self.org2],
        )
        self.taxonomy_one_org = api.create_taxonomy(
            name="OpenedX Content Types",
            enabled=True,
            org_owners=[self.org1],
        )
        # Tags
        self.tag_disabled = Tag.objects.create(
            taxonomy=self.taxonomy_disabled,
            value="learning",
        )
        self.tag_all_orgs = Tag.objects.create(
            taxonomy=self.taxonomy_all_orgs,
            value="learning",
        )
        self.tag_both_orgs = Tag.objects.create(
            taxonomy=self.taxonomy_both_orgs,
            value="learning",
        )
        self.tag_one_org = Tag.objects.create(
            taxonomy=self.taxonomy_one_org,
            value="learning",
        )
        # ObjectTags
        self.all_orgs_course_tag = api.tag_object(
            taxonomy=self.taxonomy_all_orgs,
            tags=[self.tag_all_orgs.id],
            object_id="course-v1:OeX+DemoX+Demo_Course",
        )[0]
        self.all_orgs_block_tag = api.tag_object(
            taxonomy=self.taxonomy_all_orgs,
            tags=[self.tag_all_orgs.id],
            object_id="block-v1:Ax+DemoX+Demo_Course+type@vertical+block@abcde",
        )[0]
        self.both_orgs_course_tag = api.tag_object(
            taxonomy=self.taxonomy_both_orgs,
            tags=[self.tag_both_orgs.id],
            object_id="course-v1:Ax+DemoX+Demo_Course",
        )[0]
        self.both_orgs_block_tag = api.tag_object(
            taxonomy=self.taxonomy_both_orgs,
            tags=[self.tag_both_orgs.id],
            object_id="block-v1:OeX+DemoX+Demo_Course+type@video+block@abcde",
        )[0]
        self.one_org_block_tag = api.tag_object(
            taxonomy=self.taxonomy_one_org,
            tags=[self.tag_one_org.id],
            object_id="block-v1:OeX+DemoX+Demo_Course+type@html+block@abcde",
        )[0]
        self.disabled_course_tag = api.tag_object(
            taxonomy=self.taxonomy_disabled,
            tags=[self.tag_disabled.id],
            object_id="course-v1:Ax+DemoX+Demo_Course",
        )[0]

        # Invalid object tags must be manually created
        self.all_orgs_invalid_tag = ObjectTag.objects.create(
            taxonomy=self.taxonomy_all_orgs,
            tag=self.tag_all_orgs,
            object_id="course-v1_OpenedX_DemoX_Demo_Course",
        )
        self.one_org_invalid_org_tag = ObjectTag.objects.create(
            taxonomy=self.taxonomy_one_org,
            tag=self.tag_one_org,
            object_id="block-v1_OeX_DemoX_Demo_Course_type_html_block@abcde",
        )


@ddt.ddt
class TestAPITaxonomy(TestTaxonomyMixin, TestCase):
    """
    Tests the Content Taxonomy APIs.
    """

    def test_get_taxonomies_enabled_subclasses(self):
        with self.assertNumQueries(1):
            taxonomies = list(api.get_taxonomies())
        assert taxonomies == [
            self.taxonomy_all_orgs,
            self.taxonomy_one_org,
            self.taxonomy_both_orgs,
        ]

    @ddt.data(
        # All orgs
        (None, True, ["taxonomy_all_orgs"]),
        (None, False, ["taxonomy_disabled"]),
        (None, None, ["taxonomy_all_orgs", "taxonomy_disabled"]),
        # Org 1
        ("org1", True, ["taxonomy_all_orgs", "taxonomy_one_org", "taxonomy_both_orgs"]),
        ("org1", False, ["taxonomy_disabled"]),
        (
            "org1",
            None,
            [
                "taxonomy_all_orgs",
                "taxonomy_disabled",
                "taxonomy_one_org",
                "taxonomy_both_orgs",
            ],
        ),
        # Org 2
        ("org2", True, ["taxonomy_all_orgs", "taxonomy_both_orgs"]),
        ("org2", False, ["taxonomy_disabled"]),
        (
            "org2",
            None,
            ["taxonomy_all_orgs", "taxonomy_disabled", "taxonomy_both_orgs"],
        ),
    )
    @ddt.unpack
    def test_get_taxonomies_for_org(self, org_attr, enabled, expected):
        org_owner = getattr(self, org_attr) if org_attr else None
        taxonomies = list(
            api.get_taxonomies_for_org(org_owner=org_owner, enabled=enabled)
        )
        assert taxonomies == [
            getattr(self, taxonomy_attr) for taxonomy_attr in expected
        ]

    @ddt.data(
        ("taxonomy_all_orgs", "all_orgs_course_tag"),
        ("taxonomy_all_orgs", "all_orgs_block_tag"),
        ("taxonomy_both_orgs", "both_orgs_course_tag"),
        ("taxonomy_both_orgs", "both_orgs_block_tag"),
        ("taxonomy_one_org", "one_org_block_tag"),
    )
    @ddt.unpack
    def test_get_object_tags_valid_for_org(
        self,
        taxonomy_attr,
        object_tag_attr,
    ):
        taxonomy_id = getattr(self, taxonomy_attr).id
        taxonomy = api.get_taxonomy(taxonomy_id)
        object_tag = getattr(self, object_tag_attr)
        with self.assertNumQueries(1):
            valid_tags = list(
                api.get_object_tags(
                    taxonomy=taxonomy,
                    object_id=object_tag.object_id,
                    valid_only=True,
                )
            )
        assert len(valid_tags) == 1
        assert valid_tags[0].id == object_tag.id

    @ddt.data(
        ("taxonomy_disabled", "disabled_course_tag"),
        ("taxonomy_all_orgs", "all_orgs_course_tag"),
        ("taxonomy_all_orgs", "all_orgs_block_tag"),
        ("taxonomy_all_orgs", "all_orgs_invalid_tag"),
        ("taxonomy_both_orgs", "both_orgs_course_tag"),
        ("taxonomy_both_orgs", "both_orgs_block_tag"),
        ("taxonomy_one_org", "one_org_block_tag"),
        ("taxonomy_one_org", "one_org_invalid_org_tag"),
    )
    @ddt.unpack
    def test_get_object_tags_include_invalid(
        self,
        taxonomy_attr,
        object_tag_attr,
    ):
        taxonomy_id = getattr(self, taxonomy_attr).id
        taxonomy = api.get_taxonomy(taxonomy_id)
        object_tag = getattr(self, object_tag_attr)
        with self.assertNumQueries(1):
            valid_tags = list(
                api.get_object_tags(
                    taxonomy=taxonomy,
                    object_id=object_tag.object_id,
                    valid_only=False,
                )
            )
        assert len(valid_tags) == 1
        assert valid_tags[0].id == object_tag.id

    @ddt.data(
        "all_orgs_invalid_tag",
        "one_org_invalid_org_tag",
    )
    def test_object_tag_not_valid_check_object(self, tag_attr):
        object_tag = getattr(self, tag_attr)
        assert not object_tag.is_valid()

    def test_get_tags(self):
        assert api.get_tags(self.taxonomy_all_orgs) == [self.tag_all_orgs]
