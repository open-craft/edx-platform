"""
Test cases for GDPR User Retirement Views
"""

from django.urls import reverse
from openedx.core.djangoapps.user_api.models import RetirementState, UserRetirementStatus
from rest_framework.test import APITestCase
from student.tests.factories import UserFactory


class GDPRUserRetirementViewTests(APITestCase):
    def setUp(self):
        super(GDPRUserRetirementViewTests, self).setUp()
        self.user1 = UserFactory.build(username='testuser1', email='test1@example.com', password='test1_password')
        self.user1.save()
        self.client.login(username=self.user1.username, password='test1_password')
        self.user2 = UserFactory.build(username='testuser2', email='test2@example.com', password='test2_password')
        self.user2.save()
        self.client.login(username=self.user2.username, password='test2_password')
        self.pending_state = RetirementState.objects.get(state_name='PENDING')


    def test_gdpr_user_retirement_api(self):
        user_retirement_url = reverse('gdpr_retirement_api')
        with self.settings(RETIREMENT_SERVICE_WORKER_USERNAME=self.user1.username):
            response = self.client.post(user_retirement_url, {"usernames": self.user2.username})
            assert response.status_code == 200

            retirement_status = UserRetirementStatus.objects.get(user__username=self.user2.username)
            assert retirement_status.current_state == self.pending_state
