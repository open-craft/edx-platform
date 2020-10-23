"""
Tests for the monkey patch applied to admin options in order to make course overviews work in the admin.
"""
from ddt import ddt, data, unpack
from nose.plugins.attrib import attr

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

@ddt
@attr(shard=3)
class CourseOverviewAdminTestCase(ModuleStoreTestCase):
    @unpack
    @data(
        ("CS", "GOV_CS_selfpy101", "3_2020", "course-v1:CS+GOV_CS_selfpy101+3_2020"),
        ("edX", "DemoX", "Demo_Course", "course-v1:edX+DemoX+Demo_Course"),
    )
    def test_course_overview_admin(self, org, number, run, url_key):
        """
        Test that course IDs that worked before should still work, and that course IDs that were broken should work
        now as well.
        """
        course = CourseFactory.create(
            default_store=ModuleStoreEnum.Type.split, org=org, number=number, run=run,
        )
        # Side effect: Creates a CourseOverview if it does not exist.
        CourseOverview.get_from_id(course.id)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password=self.user_password)
        response = self.client.get('/admin/course_overviews/courseoverview/')
        target_url = '/admin/course_overviews/courseoverview/{}/'.format(url_key)
        self.assertIn(target_url, response.content)
        response = self.client.get(target_url)
        self.assertEqual(response.status_code, 200)
