import ddt
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from ..api.config import get_discussion_config, get_discussion_config_options
from ..api.data import DiscussionConfigData
from ..models import DiscussionConfig, LearningContextDiscussionConfig


@ddt.ddt
class DiscussionAPITest(TestCase):

    def setUp(self):
        self.course_key = CourseKey.from_string("course-v1:testX+Course+Test_Run")
        self.course_key_without_config = CourseKey.from_string("course-v1:testY+Course+Test_Run")
        self.provider = 'test-provider'
        self.config_slug = 'test-slug'
        self.config_data = DiscussionConfigData(
            provider=self.provider,
            slug=self.config_slug,
            config={},
            private_config={},
        )
        DiscussionConfig.objects.create(
            org=self.course_key.org,
            provider=self.provider,
            slug=self.config_slug,
            enabled=True,
            config={},
            private_config={},
        )
        DiscussionConfig.objects.create(
            context_key=self.course_key,
            provider=self.provider,
            slug='another-test-slug',
            enabled=True,
            config={},
            private_config={},
        )
        LearningContextDiscussionConfig.objects.create(
            context_key=self.course_key,
            config_slug=self.config_slug,
        )

    def test_get_discussion_config_success(self):
        config = get_discussion_config(self.course_key)
        assert config == self.config_data

    def test_get_discussion_config_fail(self):
        config = get_discussion_config(self.course_key_without_config)
        assert config is None

    def test_get_discussion_config_options(self):
        options = get_discussion_config_options(self.course_key)
        assert len(options) == 2
        assert self.config_data in options
