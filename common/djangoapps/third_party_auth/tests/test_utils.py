"""
Tests for third_party_auth utility functions.
"""


import unittest
from unittest import mock
from unittest.mock import MagicMock

import ddt
from django.conf import settings

from common.djangoapps.student.tests.factories import UserFactory
from common.djangoapps.third_party_auth.tests.testutil import TestCase
from common.djangoapps.third_party_auth.utils import (
    get_associated_user_by_email_response,
    is_oauth_provider,
    user_exists,
    convert_saml_slug_provider_id,
)


@ddt.ddt
@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class TestUtils(TestCase):
    """
    Test the utility functions.
    """
    def test_user_exists(self):
        """
        Verify that user_exists function returns correct response.
        """
        # Create users from factory
        UserFactory(username='test_user', email='test_user@example.com')
        self.assertTrue(
            user_exists({'username': 'test_user', 'email': 'test_user@example.com'}),
        )
        self.assertTrue(
            user_exists({'username': 'test_user'}),
        )
        self.assertTrue(
            user_exists({'email': 'test_user@example.com'}),
        )
        self.assertFalse(
            user_exists({'username': 'invalid_user'}),
        )
        self.assertTrue(
            user_exists({'username': 'TesT_User'})
        )

    def test_convert_saml_slug_provider_id(self):
        """
        Verify saml provider id/slug map to each other correctly.
        """
        provider_names = {'saml-samltest': 'samltest', 'saml-example': 'example'}
        for provider_id in provider_names:
            # provider_id -> slug
            self.assertEqual(
                convert_saml_slug_provider_id(provider_id), provider_names[provider_id]
            )
            # slug -> provider_id
            self.assertEqual(
                convert_saml_slug_provider_id(provider_names[provider_id]), provider_id
            )

    @ddt.data(
        ('saml-farkle', False),
        ('oa2-fergus', True),
        ('oa2-felicia', True),
    )
    @ddt.unpack
    def test_is_oauth_provider(self, provider_id, oauth_provider):
        """
        Tests if the backend name is that of an auth provider or not
        """
        with mock.patch(
            'common.djangoapps.third_party_auth.utils.provider.Registry.get_from_pipeline'
        ) as get_from_pipeline:
            get_from_pipeline.return_value.provider_id = provider_id

            self.assertEqual(is_oauth_provider('backend_name'), oauth_provider)

    @ddt.data(
        (None, False),
        (None, False),
        ('The Muffin Man', True),
        ('Gingerbread Man', False),
    )
    @ddt.unpack
    def test_get_associated_user_by_email_response(self, user, user_is_active):
        """
        Tests if an association response is returned for a user
        """
        with mock.patch(
            'common.djangoapps.third_party_auth.utils.associate_by_email',
            side_effect=lambda _b, _d, u, *_a, **_k: {'user': u} if u else None,
        ):
            mock_user = MagicMock(return_value=user)
            mock_user.is_active = user_is_active

            association_response, user_is_active_resonse = get_associated_user_by_email_response(
                backend=None, details=None, user=mock_user)

            if association_response:
                self.assertEqual(association_response['user'](), user)
                self.assertEqual(user_is_active_resonse, user_is_active)
            else:
                self.assertIsNone(association_response)
                self.assertFalse(user_is_active_resonse)
