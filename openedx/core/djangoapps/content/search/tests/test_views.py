"""
Tests for the Studio content search REST API.
"""
from __future__ import annotations

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangolib.testing.utils import skip_unless_cms

from .test_api import MeilisearchTestMixin

STUDIO_SEARCH_ENDPOINT_URL = "/api/content_search/v2/studio/"


@skip_unless_cms
class StudioSearchViewTest(MeilisearchTestMixin, APITestCase):
    """
    General tests for the Studio search REST API.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff = UserFactory.create(
            username='staff', email='staff@example.com', is_staff=True, password='staff_pass'
        )
        cls.student = UserFactory.create(
            username='student', email='student@example.com', is_staff=False, password='student_pass'
        )

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    @override_settings(MEILISEARCH_ENABLED=False)
    def test_studio_search_unathenticated_disabled(self):
        """
        Whether or not Meilisearch is enabled, the API endpoint requires authentication.
        """
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 401

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_studio_search_unathenticated_enabled(self):
        """
        Whether or not Meilisearch is enabled, the API endpoint requires authentication.
        """
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 401

    @override_settings(MEILISEARCH_ENABLED=False)
    def test_studio_search_disabled(self):
        """
        When Meilisearch is disabled, the Studio search endpoint gives a 404
        """
        self.client.login(username='student', password='student_pass')
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 404

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_studio_search_student_forbidden(self):
        """
        Until we implement fine-grained permissions, only global staff can use
        the Studio search endpoint.
        """
        self.client.login(username='student', password='student_pass')
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 403

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_studio_search_staff(self):
        """
        Global staff can get a restricted API key for Meilisearch using the REST
        API.
        """
        self.client.login(username='staff', password='staff_pass')
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        assert result.data["index_name"] == "studio_content"
        assert result.data["url"].startswith("http")
        assert result.data["api_key"] and isinstance(result.data["api_key"], str)
