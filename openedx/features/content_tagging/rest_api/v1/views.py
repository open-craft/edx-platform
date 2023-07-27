"""
Tagging Org API Views
"""
from django.http import Http404
from django.db.models import Exists, OuterRef, Q

from common.djangoapps.student.roles import OrgContentCreatorRole
from openedx_tagging.core.tagging.rest_api.v1.views import TaxonomyView
from openedx_tagging.core.tagging.models import Taxonomy


from ...api import (
    create_taxonomy,
    get_taxonomy,
    get_taxonomies,
    get_taxonomies_for_org,
)
from ...models import TaxonomyOrg
from ...rules import get_user_taxonomy_orgs, is_global_taxonomy_admin
from .serializers import TaxonomyOrgListQueryParamsSerializer


class TaxonomyOrgView(TaxonomyView):
    """
    ToDo: Fix the docstring
    View to list, create, retrieve, update, or delete Taxonomies.

        NOTE: Only the GET request requires a request parameter, otherwise pass the uuid as part
        of the post body

    **List Query Parameters**
        * enabled (optional) - Filter by enabled status. Valid values: true, false, 1, 0, "true", "false", "1"
        * org (optional) - Filter by organization.

    **List Example Requests**
        GET api/tagging/v1/taxonomy                                                 - Get all taxonomies
        GET api/tagging/v1/taxonomy?enabled=true                                    - Get all enabled taxonomies
        GET api/tagging/v1/taxonomy?enabled=false                                   - Get all disabled taxonomies
        GET api/tagging/v1/taxonomy?org=A                                           - Get all taxonomies for organization A
        GET api/tagging/v1/taxonomy?org=A&enabled=true                              - Get all enabled taxonomies for organization A

    **List Query Returns**
        * 200 - Success
        * 400 - Invalid query parameter
        * 403 - Permission denied

    **Retrieve Parameters**
        * id (required): - The id of the taxonomy to retrieve

    **Retrieve Example Requests**
        GET api/tagging/v1/taxonomy/:id                                             - Get a specific taxonomy

    **Retrieve Query Returns**
        * 200 - Success
        * 404 - Taxonomy not found or User does not have permission to access the taxonomy

    **Create Parameters**
        * name (required): User-facing label used when applying tags from this taxonomy to Open edX objects.
        * description (optional): Provides extra information for the user when applying tags from this taxonomy to an object.
        * enabled (optional): Only enabled taxonomies will be shown to authors (default: true).
        * required (optional): Indicates that one or more tags from this taxonomy must be added to an object (default: False).
        * allow_multiple (optional): Indicates that multiple tags from this taxonomy may be added to an object (default: False).
        * allow_free_text (optional): Indicates that tags in this taxonomy need not be predefined; authors may enter their own tag values (default: False).

    **Create Example Requests**
        POST api/tagging/v1/taxonomy                                                - Create a taxonomy
        {
            "name": "Taxonomy Name",                    - User-facing label used when applying tags from this taxonomy to Open edX objects."
            "description": "This is a description",
            "enabled": True,
            "required": True,
            "allow_multiple": True,
            "allow_free_text": True,
        }


    **Create Query Returns**
        * 201 - Success
        * 403 - Permission denied

    **Update Parameters**
        * id (required): - The id of the taxonomy to update

    **Update Request Body**
        * name (optional): User-facing label used when applying tags from this taxonomy to Open edX objects.
        * description (optional): Provides extra information for the user when applying tags from this taxonomy to an object.
        * enabled (optional): Only enabled taxonomies will be shown to authors.
        * required (optional): Indicates that one or more tags from this taxonomy must be added to an object.
        * allow_multiple (optional): Indicates that multiple tags from this taxonomy may be added to an object.
        * allow_free_text (optional): Indicates that tags in this taxonomy need not be predefined; authors may enter their own tag values.

    **Update Example Requests**
        PUT api/tagging/v1/taxonomy/:id                                            - Update a taxonomy
        {
            "name": "Taxonomy New Name",
            "description": "This is a new description",
            "enabled": False,
            "required": False,
            "allow_multiple": False,
            "allow_free_text": True,
        }
        PATCH api/tagging/v1/taxonomy/:id                                          - Partially update a taxonomy
        {
            "name": "Taxonomy New Name",
        }

    **Update Query Returns**
        * 200 - Success
        * 403 - Permission denied

    **Delete Parameters**
        * id (required): - The id of the taxonomy to delete

    **Delete Example Requests**
        DELETE api/tagging/v1/taxonomy/:id                                         - Delete a taxonomy

    **Delete Query Returns**
        * 200 - Success
        * 404 - Taxonomy not found
        * 403 - Permission denied

    """

    def get_queryset(self):
        """
        Return a list of taxonomies.

        Returns all taxonomies by default.
        If you want the disabled taxonomies, pass enabled=False.
        If you want the enabled taxonomies, pass enabled=True.
        """
        query_params = TaxonomyOrgListQueryParamsSerializer(
            data=self.request.query_params.dict()
        )
        query_params.is_valid(raise_exception=True)
        enabled = query_params.validated_data.get("enabled", None)
        org = query_params.validated_data.get("org", None)
        taxonomies = get_taxonomies_for_org(enabled, org, False)

        if is_global_taxonomy_admin(self.request.user):
            return taxonomies
        else:
            # This should be an optional parameter on get_taxonomies_for_org?
            user_orgs = get_user_taxonomy_orgs(self.request.user)
            user_orgs_short_name = [org.short_name for org in user_orgs]
            return taxonomies.filter(
            Q(
                Exists(
                    TaxonomyOrg.objects.filter(
                        taxonomy=OuterRef("pk"),
                        rel_type=TaxonomyOrg.RelType.OWNER,
                        org__short_name__in=user_orgs_short_name,
                    )
                )
            )
            | Q(enabled=True)
        )

    def perform_create(self, serializer):
        """
        Create a new taxonomy.
        """
        serializer.instance = create_taxonomy(**serializer.validated_data)
