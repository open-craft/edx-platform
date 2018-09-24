"""
Views related to the cohorts API.
"""

from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import GenericViewSet
from edx_rest_framework_extensions.authentication import JwtAuthentication

from django.core.exceptions import ValidationError
from util.json_request import JsonResponse

from openedx.core.lib.api.authentication import (
    OAuth2AuthenticationAllowInactiveUser,
    SessionAuthenticationAllowInactiveUser
)
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin

from .forms import CohortUsersAPIForm
from .serializers import CohortUsersAPISerializer
from openedx.core.djangoapps.course_groups.models import CohortMembership


class CohortUsersViewSet(DeveloperErrorViewMixin, ListModelMixin, GenericViewSet):
    """
    **Use Cases**

        Retrieve the list of users in a cohort, add a user to a cohort or remove a user from a cohort.

    **Example Requests**:

        GET /api/cohorts/courses/{course_id}/cohorts/{cohort_id}/users/

        POST /api/cohorts/courses/{course_id}/cohorts/{cohort_id}/users/
        {
          "users": "<comma or space separated usernames>"
        }

        DELETE /api/cohorts/courses/{course_id}/cohorts/{cohort_id}/users/{username}

    **GET List of users in a cohort parameters**:

        * course_id (required): The course to which the cohort to retrieve the users for belongs to.

        * cohort_id (required): The cohort to retrieve the users for.

        * page: The (1-indexed) page to retrieve (default is 1)

        * page_size: The number of items per page (default is 10, max is 100)

    ** POST Add users to a cohort parameters**:

        * course_id (required): The course to which the cohort to add the users belongs to.

        * cohort_id (required): The cohort to add the users to.

        * users (required): A comma/space separated list usernames or email addresses of the users to add to the cohort.

    ** DELETE Remove a user from a cohort parameters**:

        * course_id (required): The course to which the cohort to remove the user from belongs to.

        * cohort_id (required): The cohort to remove the user from.

        * username (required): The username of the user to remove from the cohort.

    ** GET List of users in a cohort response Values**:

        * results: The list of users enrolled in the cohort.

            * username: Username of the user.

            * name: Full name of the user.

            * email: Email address of the user.

        * next: The URL of the next page (or null if first page).

        * previous: The URL of the previous page (or null if the last page).

    ** POST Add users to a cohort response values**:

        A HTTP 200 "OK" response code is returned.

        * added: A list of usernames/email addresses of the users who were added to the cohort.

        * changed: A list of usernames/email addresses of the users who were added to the cohort,
        changing their previous cohort assignment.

        * present: A list of usernames/email addresses of the users who are already present in the cohort.

        * unknown: A list of usernames/email address of unknown users.

        * preassigned: A list of usernames/email address of the preassigned users.

        * invalid: A list of invalid usernames/email addresses.

    ** DELETE Delete user from a cohort response values**:

        If the request for the deletion is successful or the user is not in the specified cohort,
        a HTTP 204 "No Content" response status code is returned.

        If the user does not exist, a HTTP 404 "Not Found" response status code is returned.
    """

    authentication_classes = (
        JwtAuthentication,
        OAuth2AuthenticationAllowInactiveUser,
        SessionAuthenticationAllowInactiveUser
    )
    permission_classes = (IsAdminUser, )

    def list(self, request, course_key_string, cohort_id):
        form = CohortUsersAPIForm(self.kwargs)
        if form.is_valid():
            cohort = form.cleaned_data['cohort']
            queryset = cohort.users.all()

            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = CohortUsersAPISerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        raise ValidationError(form.errors)

    def create(self, request, course_key_string, cohort_id):
        form = CohortUsersAPIForm(self.kwargs)
        if form.is_valid():
            cohort = form.cleaned_data['cohort']
            users = request.POST.get('users', '')
            results = api.add_users_to_cohort(cohort, users)
            return JsonResponse({
                'results': results
            })
        raise ValidationError(form.errors)

    def destroy(self, request, course_key_string, cohort_id, username):
        form = CohortUsersAPIForm(self.kwargs)
        if form.is_valid():
            course_key = form.cleaned_data['course_key']
            username = form.cleaned_data['username']
            try:
                api.remove_user_from_cohort(course_key, username)
            except User.DoesNotExist:
                return JsonResponse({"error": "No user '{}'".format(username)}, status=404)
            except CohortMembership.DoesNotExist:
                pass
            return JsonResponse(status=204)
        raise ValidationError(form.errors)


list_add_user_to_cohort = CohortUsersViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

remove_user_from_cohort = CohortUsersViewSet.as_view({
    'delete': 'destroy'
})
