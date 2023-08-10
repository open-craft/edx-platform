"""
API Serializers for content tagging org
"""

from rest_framework import serializers

from openedx_tagging.core.tagging.rest_api.v1.serializers import (
    TaxonomyListQueryParamsSerializer,
)

from organizations.models import Organization


class OrganizationField(serializers.Field):
    """
    Custom field for organization
    """
    def to_representation(self, value):
        return value.short_name

    def to_internal_value(self, data):
        try:
            return Organization.objects.get(short_name=data)
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Invalid organization short name"
            ) from exc


class TaxonomyOrgListQueryParamsSerializer(TaxonomyListQueryParamsSerializer):
    """
    Serializer for the query params for the GET view
    """

    org = OrganizationField(required=False)
