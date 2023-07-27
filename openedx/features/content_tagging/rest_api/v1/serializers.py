"""
API Serializers for taxonomies org
"""

from rest_framework import serializers

from openedx_tagging.core.tagging.models import Taxonomy
from openedx_tagging.core.tagging.rest_api.v1.serializers import TaxonomyListQueryParamsSerializer

from organizations.models import Organization


class OrganizationField(serializers.Field):
    def to_representation(self, value):
        return value.short_name

    def to_internal_value(self, data):
        try:
            return Organization.objects.get(short_name=data)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Invalid organization short name")

class TaxonomyOrgListQueryParamsSerializer(TaxonomyListQueryParamsSerializer):
    """
    Serializer for the query params for the GET view
    """

    org = OrganizationField(required=False)

# class TaxonomySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Taxonomy
#         fields = [
#             "id",
#             "name",
#             "description",
#             "enabled",
#             "required",
#             "allow_multiple",
#             "allow_free_text",
#             "system_defined",
#             "visible_to_authors",
#         ]


