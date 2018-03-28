"""
Customized python-social-auth backend for Oauth2 support
"""
import json

from social_core.backends.google import GoogleOAuth2
from social_core.backends.facebook import FacebookOAuth2

from utils import update_username_suggestion


class FacebookUsernameOAuthBackend(FacebookOAuth2):
    """
    Custom Backend for Facebook OAuth2 replacing the suggested username.
    """

    def get_user_details(self, response):
        user_details = super(FacebookUsernameOAuthBackend, self).get_user_details(response)
        provider_config = get_oauth_provider_config(self.name)
        user_details = update_username_suggestion(user_details, provider_config)
        return user_details


class GoogleUsernameOAuthBackend(GoogleOAuth2):
    """
    Custom Backend for Google OAuth2 replacing the suggested username.
    """

    def get_user_details(self, response):
        user_details = super(GoogleUsernameOAuthBackend, self).get_user_details(response)
        provider_config = get_oauth_provider_config(self.name)
        user_details = update_username_suggestion(user_details, provider_config)
        return user_details


def get_oauth_provider_config(name):
    """
    Get 'other_settings' from the provider config.
    """

    # Importing module here to avoid circular reference
    from .models import OAuth2ProviderConfig
    provider_config = OAuth2ProviderConfig.current(name)
    settings = json.loads(provider_config.other_settings)
    return settings
