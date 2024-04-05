"""
Tests for the Studio content search REST API.
"""
import functools
from django.test import override_settings
from rest_framework.test import APIClient
from unittest import mock

from common.djangoapps.student.auth import add_users, update_org_role
from common.djangoapps.student.roles import (
    CourseInstructorRole,
    OrgStaffRole
)
from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangoapps.content.course_overviews.tests.factories import CourseOverviewFactory
from openedx.core.djangoapps.content.search.models import SearchAccess
from openedx.core.djangolib.testing.utils import skip_unless_cms
from organizations.models import Organization
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


STUDIO_SEARCH_ENDPOINT_URL = "/api/content_search/v2/studio/"
MOCK_API_KEY_UID = "3203d764-370f-4e99-a917-d47ab7f29739"


def mock_meilisearch(enabled=True):
    """
    Decorator that mocks the required parts of content.search.views to simulate a running Meilisearch instance.
    """
    def decorator(func):
        """
        Overrides settings and patches to enable view tests.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with override_settings(
                MEILISEARCH_ENABLED=enabled,
                MEILISEARCH_PUBLIC_URL="http://meilisearch.url",
            ):
                with mock.patch(
                    'openedx.core.djangoapps.content.search.views._get_meili_api_key_uid',
                    return_value=MOCK_API_KEY_UID,
                ):
                    return func(*args, **kwargs)
        return wrapper
    return decorator


@skip_unless_cms
class StudioSearchViewTest(SharedModuleStoreTestCase):
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
        cls.staff_org = UserFactory.create(
            username='staff_org', email='staff_org@example.com', is_staff=False, password='staff_org_pass'
        )
        cls.instructor_course = UserFactory.create(
            username='instructor_course',
            email='instructor_course@example.com',
            is_staff=False,
            password='instructor_course_pass'
        )
        cls.org = Organization.objects.create(name="edX", short_name="edX")

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        course_location = self.store.make_course_key('edX', 'CreatedCourse', 'Run')
        self.course = self._create_course(course_location)
        self.course_access_keys = SearchAccess.objects.get(context_key=self.course.id).id

        update_org_role(self.staff, OrgStaffRole, self.staff_org, [self.course.id.org])

        add_users(self.staff, CourseInstructorRole(self.course.id), self.instructor_course)

    def _create_course(self, course_location):
        """
        Create dummy course and overview.
        """
        CourseFactory.create(
            org=course_location.org,
            number=course_location.course,
            run=course_location.run
        )
        course = CourseOverviewFactory.create(id=course_location, org=course_location.org)
        return course

    @mock_meilisearch(enabled=False)
    def test_studio_search_unathenticated_disabled(self):
        """
        Whether or not Meilisearch is enabled, the API endpoint requires authentication.
        """
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 401

    @mock_meilisearch(enabled=True)
    def test_studio_search_unathenticated_enabled(self):
        """
        Whether or not Meilisearch is enabled, the API endpoint requires authentication.
        """
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 401

    @mock_meilisearch(enabled=False)
    def test_studio_search_disabled(self):
        """
        When Meilisearch is disabled, the Studio search endpoint gives a 404
        """
        self.client.login(username='student', password='student_pass')
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 404

    @mock_meilisearch(enabled=True)
    def test_studio_search_enabled(self):
        """
        We've implement fine-grained permissions on the meilisearch content,
        so any logged-in user can get a restricted API key for Meilisearch using the REST API.
        """
        self.client.login(username='student', password='student_pass')
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        assert result.data["index_name"] == "studio_content"
        assert result.data["url"] == "http://meilisearch.url"
        assert result.data["api_key"] and isinstance(result.data["api_key"], str)

    def _mock_generate_tenant_token(self, mock_search_client):
        """
        Return a mocked meilisearch.Client.generate_tenant_token method.
        """
        mock_generate_tenant_token = mock.Mock(return_value='restricted_api_key')
        mock_search_client.return_value = mock.Mock(
            generate_tenant_token=mock_generate_tenant_token,
        )
        return mock_generate_tenant_token

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    def test_studio_search_student_no_access(self, mock_search_client):
        """
        Users without access to any courses or libraries will have all documents filtered out.
        """
        self.client.login(username='student', password='student_pass')
        mock_generate_tenant_token = self._mock_generate_tenant_token(mock_search_client)
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {
                    "filter": "org IN [] OR access_id IN []",
                }
            },
            expires_at=mock.ANY,
        )

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    def test_studio_search_staff(self, mock_search_client):
        """
        Users with global staff access can search any document.
        """
        self.client.login(username='staff', password='staff_pass')
        mock_generate_tenant_token = self._mock_generate_tenant_token(mock_search_client)
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {}
            },
            expires_at=mock.ANY,
        )

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    @mock.patch('openedx.core.djangoapps.content.search.views._get_meili_api_key_uid')
    def test_studio_search_org_staff(self, mock_get_api_key_uid, mock_search_client):
        """
        Org staff can access documents from its orgs
        """
        self.client.login(username='staff_org', password='staff_org_pass')
        mock_get_api_key_uid.return_value = MOCK_API_KEY_UID
        mock_generate_tenant_token = mock.Mock(return_value='restricted_api_key')
        mock_search_client.return_value = mock.Mock(
            generate_tenant_token=mock_generate_tenant_token,
        )
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200

        ### To help with debugging
        assert mock_generate_tenant_token.call_args[1]["search_rules"]["studio_content"]["filter"] == (
            "org IN ['edX'] OR access_id IN []"
        )
        ###

        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {
                    "filter": "org IN ['edX'] OR access_id IN []",
                }
            },
            expires_at=mock.ANY,
        )

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    @mock.patch('openedx.core.djangoapps.content.search.views._get_meili_api_key_uid')
    def test_studio_search_course_instructor(self, mock_get_api_key_uid, mock_search_client):
        """
        Course instructor can access documents it has direct access to
        """
        self.client.login(username='instructor_course', password='instructor_course_pass')
        mock_get_api_key_uid.return_value = MOCK_API_KEY_UID
        mock_generate_tenant_token = mock.Mock(return_value='restricted_api_key')
        mock_search_client.return_value = mock.Mock(
            generate_tenant_token=mock_generate_tenant_token,
        )
        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200

        ### To help with debugging
        assert mock_generate_tenant_token.call_args[1]["search_rules"]["studio_content"]["filter"] == (
            f"org IN [] OR access_id IN [{self.course_access_keys}]"
        )
        ###

        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {
                    "filter": f"org IN [] OR access_id IN [{self.toy_course_access_id}]",
                }
            },
            expires_at=mock.ANY,
        )

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.get_access_ids_for_request')
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    def test_studio_search_limit_access_ids(self, mock_search_client, mock_get_access_ids):
        """
        Users with access to many courses or libraries will only be able to search content
        from the most recent 1_000 courses/libraries.
        """
        self.client.login(username='student', password='student_pass')
        mock_generate_tenant_token = self._mock_generate_tenant_token(mock_search_client)
        mock_get_access_ids.return_value = list(range(2000))
        expected_access_ids = list(range(1000))

        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        mock_get_access_ids.assert_called_once()
        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {
                    "filter": f"org IN [] OR access_id IN {expected_access_ids}",
                }
            },
            expires_at=mock.ANY,
        )

    @mock_meilisearch(enabled=True)
    @mock.patch('openedx.core.djangoapps.content.search.views.get_user_orgs')
    @mock.patch('openedx.core.djangoapps.content.search.views.meilisearch.Client')
    def test_studio_search_limit_orgs(self, mock_search_client, mock_get_user_orgs):
        """
        Users with access to many courses or libraries will only be able to search content
        from the most recent 1_000 courses/libraries.
        """
        self.client.login(username='student', password='student_pass')
        mock_generate_tenant_token = self._mock_generate_tenant_token(mock_search_client)
        mock_get_user_orgs.return_value = [
            Organization.objects.create(
                short_name=f"org{x}",
                description=f"Org {x}",
            ) for x in range(2000)
        ]
        expected_user_orgs = [
            f"org{x}" for x in range(1000)
        ]

        result = self.client.get(STUDIO_SEARCH_ENDPOINT_URL)
        assert result.status_code == 200
        mock_get_user_orgs.assert_called_once()
        mock_generate_tenant_token.assert_called_once_with(
            api_key_uid=MOCK_API_KEY_UID,
            search_rules={
                "studio_content": {
                    "filter": f"org IN {expected_user_orgs} OR access_id IN []",
                }
            },
            expires_at=mock.ANY,
        )
