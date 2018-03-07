# -*- coding: utf-8 -*-
"""
Black-box tests of the DjangoUserStateClient against the semantics
defined in edx_user_state_client.
"""

from collections import defaultdict
from unittest import skip

from django.test import TestCase
from edx_user_state_client.tests import UserStateClientTestBase

from capa.tests.response_xml_factory import (
    OptionResponseXMLFactory,
)
from courseware.tests.factories import UserFactory
from courseware.user_state_client import DjangoXBlockUserStateClient
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory


class TestDjangoUserStateClient(UserStateClientTestBase, ModuleStoreTestCase):
    """
    Tests of the DjangoUserStateClient backend.
    """
    __test__ = True
    # Tell Django to clean out all databases, not just default
    multi_db = True

    def _user(self, user_idx):
        return self.users[user_idx].username

    def _block_type(self, block):
        # We only record block state history in DjangoUserStateClient
        # when the block type is 'problem'
        return 'problem'

    def setUp(self):
        super(TestDjangoUserStateClient, self).setUp()
        self.client = DjangoXBlockUserStateClient()
        self.users = defaultdict(UserFactory.create)
        self.create_course_and_problem()

    def create_course_and_problem(self):
        """
        Create a course, chapter and section and add a problem block.
        """
        # FIXME consider using the 'toy' course instead
        # FIXME use a better problem type

        self.course = CourseFactory.create(display_name='test_course', number='100')

        # Create a chapter and section in the course
        self.chapter = ItemFactory.create(
            parent_location=self.course.location,
            category='chapter'
        )

        self.section = ItemFactory.create(
            parent_location=self.chapter.location,
            display_name='my_section_1',
            category='sequential',
            metadata={'graded': True, 'format': 'My section 1'}
        )

        # Create a dropdown problem

        name = 'problem1'
        prob_xml = OptionResponseXMLFactory().build_xml(
            question_text='The correct answer is Correct',
            num_inputs=2,
            weight=2,
            options=['Correct', 'Incorrect', u'ⓤⓝⓘⓒⓞⓓⓔ'],
            correct_option='Correct'
        )

        self.problem = ItemFactory.create(
            parent_location=self.section.location,
            category='problem',
            data=prob_xml,
            metadata={'rerandomize': 'always'},
            display_name=name
        )

        # re-fetch the course from the database so the object is up to date
        # self.refresh_course()
        self.course = self.store.get_course(self.course.id)


    # We're skipping these tests because the iter_all_by_block and iter_all_by_course
    # are not implemented in the DjangoXBlockUserStateClient
    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_blocks_deleted_block(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_blocks_empty(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_blocks_many_users(self):
        pass

    def test_iter_blocks_single_user(self):
        """
        Create a user and a problem, make the user submit several answers, and check that we can get all responses.
        """
        # FIXME create a user
        # FIXME send many responses to the problem (valid, invalid, etc.)

        # FIXME get the responses and verify them
        responses = self.client.iter_all_for_block(self.problem.location)

        raise NotImplementedError()

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_course_deleted_block(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_course_empty(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_course_single_user(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_course_many_users(self):
        pass
