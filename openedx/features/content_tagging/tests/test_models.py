"""
Test for Content models
"""
import ddt
from django.test.testcases import TestCase

from openedx_tagging.core.tagging.models import (
    ObjectTag,
    Taxonomy,
    Tag,
)
from ..models import (
    ContentLanguageTaxonomy,
    ContentAuthorTaxonomy,
    ContentOrganizationTaxonomy,
)


@ddt.ddt
class TestSystemDefinedModels(TestCase):
    """
    Test for System defined models
    """

    @ddt.data(
        (ContentLanguageTaxonomy, "taxonomy"),  # Invalid object key
        (ContentLanguageTaxonomy, "tag"),  # Invalid external_id, invalid language
        (ContentLanguageTaxonomy, "object"),  # Invalid object key
        (ContentAuthorTaxonomy, "taxonomy"),  # Invalid object key
        (ContentAuthorTaxonomy, "tag"),  # Invalid external_id, User don't exits
        (ContentAuthorTaxonomy, "object"),  # Invalid object key
        (ContentOrganizationTaxonomy, "taxonomy"),  # Invalid object key
        (ContentOrganizationTaxonomy, "tag"),  # Invalid external_id, Organization don't exits
        (ContentOrganizationTaxonomy, "object"),  # Invalid object key
    )
    @ddt.unpack
    def test_validations(
        self,
        taxonomy_cls,
        check,
    ):
        """
        Test that the respective validations are being called
        """
        taxonomy = Taxonomy(
            name='Test taxonomy'
        )
        taxonomy.taxonomy_class = taxonomy_cls
        taxonomy.save()
        taxonomy = taxonomy.cast()
        tag = Tag(
            value="value",
            external_id="external_id",
        )
        tag.taxonomy = taxonomy
        tag.save()
        object_tag = ObjectTag(
            object_id='object_id',
            taxonomy=taxonomy,
            tag=tag,
        )

        check_taxonomy = check == 'taxonomy'
        check_object = check == 'object'
        check_tag = check == 'tag'
        assert not taxonomy.validate_object_tag(
            object_tag=object_tag,
            check_taxonomy=check_taxonomy,
            check_object=check_object,
            check_tag=check_tag,
        )
