"""
Tests tagging rest api views
"""

import ddt
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest import mock

from common.djangoapps.student.auth import add_users, update_org_role
from common.djangoapps.student.roles import CourseCreatorRole, OrgContentCreatorRole
from openedx_tagging.core.tagging.models import Taxonomy
from organizations.models import Organization

from openedx.features.content_tagging.models import TaxonomyOrg


User = get_user_model()



@ddt.ddt
# @mock.patch.dict("django.conf.settings.FEATURES", {"DISABLE_COURSE_CREATION":False, "ENABLE_CREATOR_GROUP": True})
@mock.patch.dict("django.conf.settings.FEATURES", {"ENABLE_CREATOR_GROUP": True})
class TestTaxonomyViewSet(APITestCase):
    def setUp(self):
        super().setUp()
        self.userS = User.objects.create(
            username="staff",
            email="staff@example.com",
            is_staff=True,
        )

        self.orgA = Organization.objects.create(
            name="Organization A", short_name="orgA"
        )
        self.orgB = Organization.objects.create(
            name="Organization B", short_name="orgB"
        )

        self.userA = User.objects.create(
            username="userA",
            email="userA@example.com",
        )
        update_org_role(self.userS, OrgContentCreatorRole, self.userA, [self.orgA.short_name])
        self.userB = User.objects.create(
            username="userB",
            email="userB@example.com",
        )
        update_org_role(self.userS, OrgContentCreatorRole, self.userB, [self.orgB.short_name])
        self.userC = User.objects.create(
            username="userC",
            email="userC@example.com",
        )
        update_org_role(
            self.userS, OrgContentCreatorRole, self.userC, [self.orgA.short_name, self.orgB.short_name]
        )

        self.st1 = Taxonomy.objects.create(
            name="st1", system_defined=True, enabled=True
        )
        TaxonomyOrg.objects.create(
            taxonomy=self.st1,
            rel_type=TaxonomyOrg.RelType.OWNER,
            org=None,
        )
        self.st2 = Taxonomy.objects.create(
            name="st2", system_defined=True, enabled=False
        )
        TaxonomyOrg.objects.create(
            taxonomy=self.st2,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )

        self.t1 = Taxonomy.objects.create(name="t1", enabled=True)
        TaxonomyOrg.objects.create(
            taxonomy=self.t1,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        self.t2 = Taxonomy.objects.create(name="t2", enabled=False)
        TaxonomyOrg.objects.create(
            taxonomy=self.t2,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )

        self.tA1 = Taxonomy.objects.create(name="tA1", enabled=True)
        TaxonomyOrg.objects.create(
            taxonomy=self.tA1,
            org=self.orgA,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        self.tA2 = Taxonomy.objects.create(name="tA2", enabled=False)
        TaxonomyOrg.objects.create(
            taxonomy=self.tA2,
            org=self.orgA,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )

        self.tB1 = Taxonomy.objects.create(name="tB1", enabled=True)
        TaxonomyOrg.objects.create(
            taxonomy=self.tB1,
            org=self.orgB,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        self.tB2 = Taxonomy.objects.create(name="tB2", enabled=False)
        TaxonomyOrg.objects.create(
            taxonomy=self.tB2,
            org=self.orgB,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )

        self.tC1 = Taxonomy.objects.create(name="tC1", enabled=True)
        TaxonomyOrg.objects.create(
            taxonomy=self.tC1,
            org=self.orgA,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        TaxonomyOrg.objects.create(
            taxonomy=self.tC1,
            org=self.orgB,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        self.tC2 = Taxonomy.objects.create(name="tC2", enabled=False)
        TaxonomyOrg.objects.create(
            taxonomy=self.tC2,
            org=self.orgA,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )
        TaxonomyOrg.objects.create(
            taxonomy=self.tC2,
            org=self.orgB,
            rel_type=TaxonomyOrg.RelType.OWNER,
        )

    @ddt.data(
        ("userA", None, None, ("st1", "t1", "tA1", "tA2", "tB1", "tC1", "tC2")),
        ("userB", None, None, ("st1", "t1", "tA1", "tB1", "tB2", "tC1", "tC2")),
        ("userC", None, None, ("st1", "t1", "tA1", "tA2", "tB1", "tB2", "tC1", "tC2")),
        (
            "userS",
            None,
            None,
            ("st1", "st2", "t1", "t2", "tA1", "tA2", "tB1", "tB2", "tC1", "tC2"),
        ),
        ("userA", True, None, ("st1", "t1", "tA1", "tB1", "tC1")),
        ("userB", True, None, ("st1", "t1", "tA1", "tB1", "tC1")),
        ("userC", True, None, ("st1", "t1", "tA1", "tB1", "tC1")),
        ("userS", True, None, ("st1", "t1", "tA1", "tB1", "tC1")),
        ("userA", False, None, ("tA2", "tC2")),
        ("userB", False, None, ("tB2", "tC2")),
        ("userC", False, None, ("tA2", "tB2", "tC2")),
        ("userS", False, None, ("st2", "t2", "tA2", "tB2", "tC2")),
        ("userA", None, "orgA", ("st1", "t1", "tA1", "tA2", "tC1", "tC2")),
        ("userB", None, "orgA", ("st1", "t1", "tA1", "tC1", "tC2")),
        (
            "userC",
            None,
            "orgA",
            ("st1", "t1", "tA1", "tA2", "tC1", "tC2"),
        ),
        (
            "userS",
            None,
            "orgA",
            ("st1", "st2", "t1", "t2", "tA1", "tA2", "tC1", "tC2"),
        ),
        ("userA", True, "orgA", ("st1", "t1", "tA1", "tC1")),
        ("userB", True, "orgA", ("st1", "t1", "tA1", "tC1")),
        ("userC", True, "orgA", ("st1", "t1", "tA1", "tC1")),
        ("userS", True, "orgA", ("st1", "t1", "tA1", "tC1")),
        ("userA", False, "orgA", ("tA2", "tC2")),
        ("userB", False, "orgA", ("tC2", )),
        ("userC", False, "orgA", ("tA2", "tC2")),
        ("userS", False, "orgA", ("st2", "t2", "tA2", "tC2")),
    )
    @ddt.unpack
    def test_list_taxonomy(self, user_attr, enabled_parameter, org_name, expected_taxonomies):
        url = reverse("content_tagging:taxonomy-list")

        if user_attr:
            user = getattr(self, user_attr)
            self.client.force_authenticate(user=user)


        query_params = {k: v for k, v in {"enabled": enabled_parameter, "org": org_name}.items() if v is not None}

        response = self.client.get(url, query_params, format="json")

        assert response.status_code == status.HTTP_200_OK
        self.assertEqual(
            set([t["name"] for t in response.data["results"]]), set(expected_taxonomies)
        )
        assert len(response.data["results"]) == len(expected_taxonomies)

    # ToDo: Verify this test
    # @ddt.data(
    #     (
    #         {"DISABLE_COURSE_CREATION": False, "ENABLE_CREATOR_GROUP": False},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_200_OK},
    #             {"user_attr": "staff", "expected_status": status.HTTP_200_OK},
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_200_OK,
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_200_OK,
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": False, "ENABLE_CREATOR_GROUP": True},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "staff", "expected_status": status.HTTP_200_OK},
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_200_OK,
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": True, "ENABLE_CREATOR_GROUP": False},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "staff", "expected_status": status.HTTP_200_OK},
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": True, "ENABLE_CREATOR_GROUP": True},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "staff", "expected_status": status.HTTP_200_OK},
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #         ),
    #     ),
    # )
    # @ddt.unpack
    # def test_list_taxonomy(self, features_dict, test_list):
    #     Taxonomy.objects.create(name="Taxonomy enabled 1", enabled=True).save()
    #     Taxonomy.objects.create(name="Taxonomy enabled 2", enabled=True).save()
    #     Taxonomy.objects.create(name="Taxonomy disabled", enabled=False).save()

    #     url = reverse("content_tagging:taxonomy-list")

    #     for test in test_list:
    #         user_attr = test["user_attr"]
    #         expected_status = test["expected_status"]

    #         if user_attr:
    #             user = getattr(self, user_attr)
    #             self.client.force_authenticate(user=user)

    #         with mock.patch.dict("django.conf.settings.FEATURES", features_dict):
    #             response = self.client.get(url)
    #         assert response.status_code == expected_status

    # ToDo: Wait definition for taxonomy detail permissions
    # @ddt.data(
    #     (None, {"enabled": True}, status.HTTP_403_FORBIDDEN),
    #     (None, {"enabled": False}, status.HTTP_403_FORBIDDEN),
    #     (
    #         "user",
    #         {"enabled": True},
    #         status.HTTP_200_OK,
    #     ),  # ToDo: Verify permission for user
    #     ("user", {"enabled": False}, status.HTTP_404_NOT_FOUND),
    #     ("staff", {"enabled": True}, status.HTTP_200_OK),
    #     ("staff", {"enabled": False}, status.HTTP_200_OK),
    # )
    # @ddt.unpack
    # def test_detail_taxonomy(self, user_attr, taxonomy_data, expected_status):
    #     create_data = {**{"name": "taxonomy detail test"}, **taxonomy_data}
    #     taxonomy = Taxonomy.objects.create(**create_data)
    #     url = reverse("content_tagging:taxonomy-detail", kwargs={"pk": taxonomy.id})

    #     if user_attr:
    #         user = getattr(self, user_attr)
    #         self.client.force_authenticate(user=user)

    #     response = self.client.get(url)
    #     assert response.status_code == expected_status

    #     if status.is_success(expected_status):
    #         self.assertGreaterEqual(response.data.items(), create_data.items())

    # ToDo: Verifty this test
    # @ddt.data(
    #     (
    #         {"DISABLE_COURSE_CREATION": False, "ENABLE_CREATOR_GROUP": False},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_201_CREATED},
    #             {
    #                 "user_attr": "staff",
    #                 "expected_status": status.HTTP_405_METHOD_NOT_ALLOWED,  # ToDo: Verify error status 405
    #             },
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_405_METHOD_NOT_ALLOWED,  # ToDo: Verify error status 405
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_405_METHOD_NOT_ALLOWED,  # ToDo: Verify error status 405
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": False, "ENABLE_CREATOR_GROUP": True},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {
    #                 "user_attr": "staff",
    #                 "expected_status": status.HTTP_201_CREATED,
    #             },
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_405_METHOD_NOT_ALLOWED,  # ToDo: Verify error status 405
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": True, "ENABLE_CREATOR_GROUP": False},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "staff", "expected_status": status.HTTP_201_CREATED},
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #         ),
    #     ),
    #     (
    #         {"DISABLE_COURSE_CREATION": True, "ENABLE_CREATOR_GROUP": True},
    #         (
    #             {"user_attr": None, "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "user", "expected_status": status.HTTP_403_FORBIDDEN},
    #             {"user_attr": "staff", "expected_status": status.HTTP_201_CREATED},
    #             {
    #                 "user_attr": "user_group_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #             {
    #                 "user_attr": "user_org_content_creator",
    #                 "expected_status": status.HTTP_403_FORBIDDEN,
    #             },
    #         ),
    #     ),
    # )
    # @ddt.unpack
    # def test_create_taxonomy(self, features_dict, test_list):
    #     url = reverse("content_tagging:taxonomy-list")

    #     create_data = {
    #         "name": "taxonomy_data_2",
    #         "description": "This is a description",
    #         "enabled": True,
    #         "required": True,
    #         "allow_multiple": True,
    #     }

    #     for test in test_list:
    #         user_attr = test["user_attr"]
    #         expected_status = test["expected_status"]

    #         if user_attr:
    #             user = getattr(self, user_attr)
    #             self.client.force_authenticate(user=user)

    #         with mock.patch.dict("django.conf.settings.FEATURES", features_dict):
    #             response = self.client.post(url, create_data)
    #             assert response.status_code == expected_status

    #             # If we were able to create the taxonomy, check if it was created
    #             if status.is_success(expected_status):
    #                 self.assertGreaterEqual(response.data.items(), create_data.items())
    #                 url = reverse(
    #                     "content_tagging:taxonomy-detail",
    #                     kwargs={"pk": response.data["id"]},
    #                 )
    #                 response = self.client.get(url)
    #                 self.assertGreaterEqual(response.data.items(), create_data.items())

    # ToDo: Waiting validation of test_create_taxonomy
    # @ddt.data(
    #     (None, status.HTTP_403_FORBIDDEN),
    #     ("user", status.HTTP_404_NOT_FOUND),
    #     ("staff", status.HTTP_200_OK),
    # )
    # @ddt.unpack
    # def test_update_taxonomy(self, user_attr, expected_status):
    #     taxonomy = Taxonomy.objects.create(
    #         name="test update taxonomy",
    #         description="taxonomy description",
    #         enabled=False,
    #     )
    #     taxonomy.save()

    #     url = reverse("content_tagging:taxonomy-detail", kwargs={"pk": taxonomy.id})

    #     if user_attr:
    #         user = getattr(self, user_attr)
    #         self.client.force_authenticate(user=user)

    #     response = self.client.put(url, {"name": "new name"})
    #     assert response.status_code == expected_status

    #     # If we were able to update the taxonomy, check if the name changed
    #     if status.is_success(expected_status):
    #         response = self.client.get(url)
    #         self.assertEqual(response.data["name"], "new name")
    #         self.assertEqual(response.data["enabled"], False)
    #         self.assertEqual(response.data["description"], "taxonomy description")

    # ToDo: Verify this test
    # def test_update_taxonomy_system_defined(self):
    #     taxonomy = Taxonomy.objects.create(
    #         name="test system taxonomy", system_defined=True
    #     )
    #     taxonomy.save()
    #     url = reverse("content_tagging:taxonomy-detail", kwargs={"pk": taxonomy.id})

    #     self.client.force_authenticate(user=self.staff)
    #     response = self.client.put(url, {"name": "new name"})
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ToDo: Waiting validation of test_create_taxonomy
    # @ddt.data(
    #     (None, status.HTTP_403_FORBIDDEN),
    #     ("user", status.HTTP_404_NOT_FOUND),
    #     ("staff", status.HTTP_200_OK),
    # )
    # @ddt.unpack
    # def test_patch_taxonomy(self, user_attr, expected_status):
    #     taxonomy = Taxonomy.objects.create(name="test patch taxonomy", enabled=False)
    #     taxonomy.save()

    #     url = reverse("content_tagging:taxonomy-detail", kwargs={"pk": taxonomy.id})

    #     if user_attr:
    #         user = getattr(self, user_attr)
    #         self.client.force_authenticate(user=user)

    #     response = self.client.patch(url, {"name": "new name"})
    #     self.assertEqual(response.status_code, expected_status)

    #     # If we were able to update the taxonomy, check if the name changed
    #     if status.is_success(expected_status):
    #         response = self.client.get(url)
    #         self.assertEqual(response.data["name"], "new name")
    #         self.assertEqual(response.data["enabled"], False)

    # ToDo: Waiting validation of test_create_taxonomy
    # @ddt.data(
    #     (None, status.HTTP_403_FORBIDDEN),
    #     ("user", status.HTTP_403_FORBIDDEN),
    #     ("staff", status.HTTP_204_NO_CONTENT),
    # )
    # @ddt.unpack
    # def test_delete_taxonomy(self, user_attr, expected_status):
    #     taxonomy = Taxonomy.objects.create(name="test delete taxonomy")
    #     taxonomy.save()

    #     url = reverse("content_tagging:taxonomy-detail", kwargs={"pk": taxonomy.id})

    #     if user_attr:
    #         user = getattr(self, user_attr)
    #         self.client.force_authenticate(user=user)

    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, expected_status)

    #     # If we were able to delete the taxonomy, check that it's really gone
    #     if status.is_success(expected_status):
    #         response = self.client.get(url)
    #         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
