"""
Test batch_get_or_create in ExternalId model
"""

from django.test import TestCase
from common.djangoapps.student.tests.factories import UserFactory
from openedx.core.djangoapps.external_user_ids.models import ExternalId
from openedx.core.djangoapps.external_user_ids.tests.factories import ExternalIDTypeFactory


class TestBatchGenerateExternalIds(TestCase):
    """
    Test ExternalId.batch_get_or_create
    """

    def test_batch_get_or_create(self):
        """
        Test if batch_get_or_create creates ExternalIds in batch
        """
        id_type = ExternalIDTypeFactory.create(name='test')
        users = [UserFactory() for _ in range(10)]
        external_ids = ExternalId.batch_get_or_create(users, id_type)
        assert len(external_ids) == len(users)
        assert external_ids[0].user in users
        assert external_ids[0].external_id_type.name == 'test'

        # Test with some user that already has ExternalIds
        users += [UserFactory() for _ in range(5)]
        external_ids = ExternalId.batch_get_or_create(users, id_type)
        assert len(external_ids) == len(users)

    def test_batch_get_or_create_wrong_type(self):
        """
        Test if batch_get_or_create returns None if wrong type given
        """
        users = [UserFactory() for _ in range(2)]
        external_ids = ExternalId.batch_get_or_create(users, 'invalid')
        assert external_ids is None
