"""
Slightly customized python-social-auth backend for Oauth2 support
"""
from utils import UsernameGenerator, generate_username

from django.contrib.auth.models import User

from social_core.backends.google import GoogleOAuth2
from social_core.backends.facebook import FacebookOAuth2


class HintGenerator(object):
    """
    Helper class to process the username.
    """

    def process_username(self, user_details):
        """
        By default, FacebookOAuth2 has the username same as full name.

        For example:
            {'username': u'Diego Rojas Torrado', 'fullname': u'Diego Rojas Torrado'}

        But in the frontend, the username is rendered as a string without whitespaces.
        We can't get the value of username key as the final object, we need to process it
        converting it in a string without whitespaces same as happens in the frontend.

        With GoogleOAuth2 this does not happens, but in order to avoid DRY, anyway we pass
        the string to the replace function.
        """
        get_username = user_details['username']
        rendered_username = get_username.replace(' ', '')
        new_username = generate_username(rendered_username)
        user_details.update({'username': new_username})
        return user_details


class FacebookUsernameOAuthBackend(FacebookOAuth2):
    """
    Backend for Facebook OAuth2
    """

    def get_user_details(self, response):
        user_details = super(FacebookUsernameOAuthBackend, self).get_user_details(response)
        generator = HintGenerator()
        hint_username = generator.process_username(user_details)
        return hint_username


class GoogleUsernameOAuthBackend(GoogleOAuth2):
    """
    Backend for Google OAuth2
    """

    def get_user_details(self, response):
        user_details = super(GoogleUsernameOAuthBackend, self).get_user_details(response)
        generator = HintGenerator()
        hint_username = generator.process_username(user_details)
        return hint_username
