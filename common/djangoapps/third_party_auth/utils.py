"""
Utility functions for third_party_auth
"""

from uuid import UUID
from django.contrib.auth.models import User
from social_core.pipeline.social_auth import associate_by_email

from common.djangoapps.third_party_auth.models import OAuth2ProviderConfig
from . import provider


def user_exists(details):
    """
    Return True if user with given details exist in the system.

    Arguments:
        details (dict): dictionary containing user infor like email, username etc.

    Returns:
        (bool): True if user with given details exists, `False` otherwise.
    """
    user_queryset_filter = {}
    email = details.get('email')
    username = details.get('username')
    if email:
        user_queryset_filter['email'] = email
    elif username:
        user_queryset_filter['username__iexact'] = username

    if user_queryset_filter:
        return User.objects.filter(**user_queryset_filter).exists()

    return False


def convert_saml_slug_provider_id(provider):
    """
    Provider id is stored with the backend type prefixed to it (ie "saml-")
    Slug is stored without this prefix.
    This just converts between them whenever you expect the opposite of what you currently have.

    Arguments:
        provider (string): provider_id or slug

    Returns:
        (string): Opposite of what you inputted (slug -> provider_id; provider_id -> slug)
    """
    if provider.startswith('saml-'):
        return provider[5:]
    else:
        return 'saml-' + provider


def validate_uuid4_string(uuid_string):
    """
    Returns True if valid uuid4 string, or False
    """
    try:
        UUID(uuid_string, version=4)
    except ValueError:
        return False
    return True


def is_oauth_provider(backend_name, **kwargs):
    """
    Verify that the third party provider uses oauth
    """
    current_provider = provider.Registry.get_from_pipeline({'backend': backend_name, 'kwargs': kwargs})
    if current_provider:
        return current_provider.provider_id.startswith(OAuth2ProviderConfig.prefix)

    return False


def get_associated_user_by_email_response(backend, details, user, *args, **kwargs):
    """
    Gets the user associated by the `associate_by_email` social auth method
    """

    association_response = associate_by_email(backend, details, user, *args, **kwargs)

    if (
        association_response and
        association_response.get('user')
    ):
        # Only return the user matched by email if their email has been activated.
        # Otherwise, an illegitimate user can create an account with another user's
        # email address and the legitimate user would now login to the illegitimate
        # account.
        return (association_response, association_response['user'].is_active)

    return (None, False)
