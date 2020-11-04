import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from rest_framework.test import APIClient, APITestCase

from student.tests.factories import UserFactory


class ProgressMigrateAPITestCase(APITestCase):
    def setUp(self):
        super(ProgressMigrateAPITestCase, self).setUp()

        test_password = 'password'

        self.api_client = APIClient()
        self.user = UserFactory(is_staff=True, password=test_password)
        self.api_client.login(username=self.user.username, password=test_password)

        self.url = reverse('progress_migrate')

    def test_invalid_csv(self):
        invalid_csv = b'course,source_email,wrong_column,outcome\r\n' \
            'course-v1:a+b+c,source@example.com,target@example.com,\r\n'

        csv_file = SimpleUploadedFile("migrate.csv", invalid_csv, content_type="text/csv")

        response = self.api_client.post(
            self.url, {"file": csv_file}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    @mock.patch('openedx.core.djangoapps.user_api.completion.views.migrate_progress.delay')
    def test_migrate_scheduling(self, migrate_progress):
        csv = b'course,source_email,dest_email,outcome\r\n' \
            'course-v1:a+b+c,source@example.com,target@example.com,\r\n'

        csv_file = SimpleUploadedFile("migrate.csv", csv, content_type="text/csv")

        response = self.api_client.post(
            self.url, {"recepient_address": self.user.email, "file": csv_file}, format="multipart"
        )

        self.assertEqual(response.status_code, 204)

        migrate_progress.assert_called_with(
            [('course-v1:a+b+c', 'source@example.com', 'target@example.com')],
            [self.user.email]
        )
