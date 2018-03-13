# -*- coding: utf-8 -*-
"""
Black-box tests of the DjangoUserStateClient against the semantics
defined in edx_user_state_client.
"""

from collections import defaultdict
from six import text_type
from unittest import skip

from django.core.urlresolvers import reverse
from django.test import TestCase
from edx_user_state_client.tests import UserStateClientTestBase

from capa.tests.response_xml_factory import (
    OptionResponseXMLFactory,
)
from courseware.tests.factories import UserFactory
from courseware.user_state_client import DjangoXBlockUserStateClient
from openedx.core.lib.url_utils import quote_slashes
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
        # super(TestDjangoUserStateClient, self).setUp()

        # Both ModuleStoreTestCase and UserStateClientTestBase want to store things in a field called tha same
        # (self.client), the former to store Django's browser simulator, the latter to store UserStateClient.
        # We manually call the parent classes and rename Django's client to testclient

        ModuleStoreTestCase.setUp(self)
        self.testclient = self.client

        UserStateClientTestBase.setUp(self)
        self.client = DjangoXBlockUserStateClient()

        # FIXME delete the "users" part, replace it with the next part. Or actually support 2 users
        self.users = defaultdict(UserFactory.create)

        # Log the "testuser" user in
        self.user.set_password('xyz')
        self.user.save()
        self.testclient.login(username=self.user.username,password='xyz')


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

    # FIXME needed? Replace by ProblemSubmissionTestMixin?
    def problem_location(self, problem_url_name):
        """
        Returns the url of the problem given the problem's name
        """
        return self.course.id.make_usage_key('problem', problem_url_name)

    # FIXME needed? Replace by ProblemSubmissionTestMixin?
    def submit_question_answer(self, problem_url_name, responses):
        """
        Submit answers to a question.

        Responses is a dict mapping problem ids to answers:
            {'2_1': 'Correct', '2_2': 'Incorrect'}
        """

        problem_location = self.problem_location(problem_url_name)

        # FIXME delete the lines before, and the problem_location() function. For now I load always the same problem
        problem_location = self.problem.location

        modx_url = self.modx_url(problem_location, 'problem_check')

        answer_key_prefix = 'input_{}_'.format(problem_location.html_id())

        # format the response dictionary to be sent in the post request by adding the above prefix to each key
        response_dict = {(answer_key_prefix + k): v for k, v in responses.items()}
        resp = self.testclient.post(modx_url, response_dict)

        return resp

    # FIXME needed? Replace by ProblemSubmissionTestMixin?
    def modx_url(self, problem_location, dispatch):
        """
        Return the url needed for the desired action.

        problem_location: location of the problem on which we want some action

        dispatch: the the action string that gets passed to the view as a kwarg
            example: 'check_problem' for having responses processed
        """
        return reverse(
            'xblock_handler',
            kwargs={
                'course_id': text_type(self.course.id),
                'usage_id': quote_slashes(text_type(problem_location)),
                'handler': 'xmodule_handler',
                'suffix': dispatch,
            }
        )

    # We're skipping these tests because the iter_all_by_block and iter_all_by_course
    # are not implemented in the DjangoXBlockUserStateClient
    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_blocks_deleted_block(self):
        # FIXME implement
        pass

    def test_iter_blocks_empty(self):
        """
        Don't submit responses, then check that we get an empty list.
        """
        # FIXME test
        self.assertItemsEqual(
            self.client.iter_all_for_block(self.problem.location),
            []
        )
        pass

    @skip("Not supported by DjangoXBlockUserStateClient")
    def test_iter_blocks_many_users(self):
        # FIXME implement
        pass

    def test_iter_blocks_single_user(self):
        """
        Create a user and a problem, make the user submit several answers, and check that we can get all responses.
        """
        
        # FIXME send many responses to the problem (valid, invalid, etc.)

        resp = self.submit_question_answer('p1', {'2_1': 'Correct'})

        # FIXME get the responses and verify them
        responses = self.client.iter_all_for_block(self.problem.location)
        responses = list(responses)

        # FIXME remove prints etc.
        print(responses)
        from courseware.models import BaseStudentModuleHistory, StudentModule
        print(StudentModule.objects.all())

        # FIXME improve a bit the tests for the right answers. Simplify
        self.assertEquals(len(responses), 1)
        answers = responses[0].state['student_answers'].values()
        self.assertEquals(len(answers), 1)
        self.assertEquals(answers[0], "Correct")

        # FIXME delete
        # self.assertItemsEqual(
        #     [item.state for item in responses],
        #     [{"correct_map": {"i4x-org_64-100-problem-problem1_2_1": {"hint": "", "hintmode": None, "correctness": "correct", "msg": "", "answervariable": None, "npoints": None, "queuestate": None}, "i4x-org_64-100-problem-problem1_2_2": {"hint": "", "hintmode": None, "correctness": "incorrect", "msg": "", "answervariable": None, "npoints": None, "queuestate": None}}, "input_state": {"i4x-org_64-100-problem-problem1_2_1": {}, "i4x-org_64-100-problem-problem1_2_2": {}}, "last_submission_time": "2018-03-13T16:51:23Z", "attempts": 1, "score": {"raw_earned": 1, "raw_possible": 2}, "done": True, "student_answers": {"i4x-org_64-100-problem-problem1_2_1": "Correct"}, "seed": 121}]
        # )


        raise NotImplementedError()

    @skip("Not supported by DjangoXBlockUserStateClient, because iter_all_for_course is unimplemented")
    def test_iter_course_deleted_block(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient, because iter_all_for_course is unimplemented")
    def test_iter_course_empty(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient, because iter_all_for_course is unimplemented")
    def test_iter_course_single_user(self):
        pass

    @skip("Not supported by DjangoXBlockUserStateClient, because iter_all_for_course is unimplemented")
    def test_iter_course_many_users(self):
        pass
