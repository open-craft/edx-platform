"""
Test batch_get_or_create in ExternalId model
"""

from django.test import TestCase
from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangoapps.external_user_ids.models import ExternalId
from openedx.core.djangoapps.external_user_ids.tests.factories import ExternalIDTypeFactory


class TestBatchGenerateExternalIds(TestCase):
    """
    Test ExternalId.batch_get_or_create_user_ids
    """

    def test_batch_get_or_create_user_ids(self):
        """
        Test if batch_get_or_create creates ExternalIds in batch
        """
        id_type = ExternalIDTypeFactory.create(name='test')
        users = [UserFactory() for _ in range(10)]
        result = ExternalId.batch_get_or_create_user_ids(users, id_type)
        assert len(result) == len(result)

        for user in users:
            externalid, created = result[user.id]
            assert externalid.external_id_type.name == 'test'
            assert externalid.user == user

            # all should be newly created
            assert created

    def test_batch_get_or_create_user_ids_existing_ids(self):
        """
        Test batch creation output when there are existing ids for some user
        """
        id_type = ExternalIDTypeFactory.create(name='test')

        # first let's create some user and externalids for them
        users = [UserFactory() for _ in range(10)]
        result = ExternalId.batch_get_or_create_user_ids(users, id_type)

        # now create some new user and try to create externalids for all user
        new_users = [UserFactory() for _ in range(5)]
        all_users = users + new_users
        result = ExternalId.batch_get_or_create_user_ids(all_users, id_type)

        assert len(result) == len(all_users)

        # old users should have created flag False
        for user in users:
            assert result[user.id][1] is False

        # new users should have created flag True
        for user in new_users:
            assert result[user.id][1] is True

    def test_batch_get_or_create_user_ids_wrong_type(self):
        """
        Test if batch_get_or_create returns None if wrong type given
        """
        users = [UserFactory() for _ in range(2)]
        external_ids = ExternalId.batch_get_or_create_user_ids(users, 'invalid')
        assert external_ids is None
