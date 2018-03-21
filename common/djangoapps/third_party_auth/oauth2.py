"""
Slightly customized python-social-auth backend for Oauth2 support
"""
from social_core.backends.google import GoogleOAuth2
from social_core.backends.facebook import FacebookOAuth2

from utils import update_username_suggestion


class FacebookUsernameOAuthBackend(FacebookOAuth2):
    """
    Custom Backend for Facebook OAuth2 replacing the suggested username
    """

    def get_user_details(self, response):
        user_details = super(FacebookUsernameOAuthBackend, self).get_user_details(response)
        update_username_suggestion(user_details)
        return user_details


class GoogleUsernameOAuthBackend(GoogleOAuth2):
    """
    Custom Backend for Google OAuth2 replacing the suggested username
    """

    def get_user_details(self, response):
        user_details = super(GoogleUsernameOAuthBackend, self).get_user_details(response)
        update_username_suggestion(user_details)
        return user_details
