"""
Serializers for Collections.
"""

from rest_framework import serializers
from lms.djangoapps.blockstore.apps.bundles.models import Collection
from ... import relations


class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for the Collection model.
    """

    class Meta:

        model = Collection

        fields = (
            'title',
            'url',
            'uuid',
        )

    url = relations.HyperlinkedIdentityField(
        lookup_field='uuid',
        lookup_url_kwarg='uuid',
        view_name='blockstore_api:blockstore_api_v1:collection-detail',
    )
