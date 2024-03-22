""" Tests calling the grades api directly """


from unittest.mock import patch, Mock

import ddt

from common.djangoapps.student.tests.factories import UserFactory
from lms.djangoapps.grades import api
from lms.djangoapps.grades.models import (
    PersistentSubsectionGrade,
    PersistentSubsectionGradeOverride,
    PersistentCourseGrade
)
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase  # lint-amnesty, pylint: disable=wrong-import-order
from xmodule.modulestore.tests.factories import CourseFactory, BlockFactory  # lint-amnesty, pylint: disable=wrong-import-order


@ddt.ddt
class OverrideSubsectionGradeTests(ModuleStoreTestCase):
    """
    Tests for the override subsection grades api call
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory()
        cls.overriding_user = UserFactory()
        cls.signal_patcher = patch('lms.djangoapps.grades.signals.signals.SUBSECTION_OVERRIDE_CHANGED.send')
        cls.signal_patcher.start()
        cls.id_patcher = patch('lms.djangoapps.grades.api.create_new_event_transaction_id')
        cls.mock_create_id = cls.id_patcher.start()
        cls.mock_create_id.return_value = 1
        cls.type_patcher = patch('lms.djangoapps.grades.api.set_event_transaction_type')
        cls.type_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.signal_patcher.stop()
        cls.id_patcher.stop()
        cls.type_patcher.stop()

    def setUp(self):
        super().setUp()
        self.course = CourseFactory.create(org='edX', number='DemoX', display_name='Demo_Course', run='Spring2019')
        self.subsection = BlockFactory.create(parent=self.course, category="sequential", display_name="Subsection")
        self.grade = PersistentSubsectionGrade.update_or_create_grade(
            user_id=self.user.id,
            course_id=self.course.id,
            usage_key=self.subsection.location,
            first_attempted=None,
            visible_blocks=[],
            earned_all=6.0,
            possible_all=6.0,
            earned_graded=5.0,
            possible_graded=5.0
        )

    def tearDown(self):
        super().tearDown()
        PersistentSubsectionGradeOverride.objects.all().delete()

    @ddt.data(0.0, None, 3.0)
    def test_override_subsection_grade(self, earned_graded):
        api.override_subsection_grade(
            self.user.id,
            self.course.id,
            self.subsection.location,
            overrider=self.overriding_user,
            earned_graded=earned_graded,
            comment='Test Override Comment',
        )
        override_obj = api.get_subsection_grade_override(
            self.user.id,
            self.course.id,
            self.subsection.location
        )
        assert override_obj is not None
        assert override_obj.earned_graded_override == earned_graded
        assert override_obj.override_reason == 'Test Override Comment'

        for i in range(3):
            override_obj.override_reason = 'this field purposefully left blank'
            override_obj.earned_graded_override = i
            override_obj.save()

        api.override_subsection_grade(
            self.user.id,
            self.course.id,
            self.subsection.location,
            overrider=self.overriding_user,
            earned_graded=earned_graded,
            comment='Test Override Comment 2',
        )
        override_obj = api.get_subsection_grade_override(
            self.user.id,
            self.course.id,
            self.subsection.location
        )

        assert override_obj is not None
        assert override_obj.earned_graded_override == earned_graded
        assert override_obj.override_reason == 'Test Override Comment 2'

        assert 5 == len(override_obj.history.all())
        for history_entry in override_obj.history.all():
            if history_entry.override_reason.startswith('Test Override Comment'):
                assert self.overriding_user == history_entry.history_user
                assert self.overriding_user.id == history_entry.history_user_id
            else:
                assert history_entry.history_user is None
                assert history_entry.history_user_id is None


class ClearGradeTests(ModuleStoreTestCase):
    """
    Tests for the clearing grades api call
    """
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory()
        cls.overriding_user = UserFactory()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.course = CourseFactory.create(org='edX', number='DemoX', display_name='Demo_Course', run='Spring2019')
        self.subsection = BlockFactory.create(parent=self.course, category="sequential", display_name="Subsection")
        self.grade = PersistentSubsectionGrade.update_or_create_grade(
            user_id=self.user.id,
            course_id=self.course.id,
            usage_key=self.subsection.location,
            first_attempted=None,
            visible_blocks=[],
            earned_all=6.0,
            possible_all=6.0,
            earned_graded=5.0,
            possible_graded=5.0
        )
        self.params = {
            "user_id": self.user.id,
            "course_id": self.course.id,
            "course_version": "JoeMcEwing",
            "percent_grade": 77.7,
            "letter_grade": "Great job",
            "passed": True,
        }
        PersistentCourseGrade.update_or_create(**self.params)

    def tearDown(self):
        super().tearDown()
        PersistentSubsectionGradeOverride.objects.all().delete()  # clear out all previous overrides

    def test_clear_user_course_grades(self):
        api.override_subsection_grade(
            self.user.id,
            self.course.id,
            self.subsection.location,
            overrider=self.overriding_user,
            earned_graded=0.0,
            comment='Test Override Comment',
        )
        override_obj = api.get_subsection_grade_override(
            self.user.id,
            self.course.id,
            self.subsection.location
        )
        course_grade = PersistentCourseGrade.read(self.user.id, self.course.id)
        self.assertIsNotNone(course_grade)
        self.assertIsNotNone(override_obj)

        api.clear_user_course_grades(self.user.id, self.course.id)
        with self.assertRaises(PersistentCourseGrade.DoesNotExist):
            PersistentCourseGrade.read(self.user.id, self.course.id)

        with self.assertRaises(PersistentSubsectionGrade.DoesNotExist):
            api.get_subsection_grade_override(
                self.user.id,
                self.course.id,
                self.subsection.location
            )

    def test_clear_wrong_user_course_grades(self):
        wrong_user = UserFactory()
        api.override_subsection_grade(
            self.user.id,
            self.course.id,
            self.subsection.location,
            overrider=self.overriding_user,
            earned_graded=0.0,
            comment='Test Override Comment',
        )
        override_obj = api.get_subsection_grade_override(
            self.user.id,
            self.course.id,
            self.subsection.location
        )
        course_grade = PersistentCourseGrade.read(self.user.id, self.course.id)
        self.assertIsNotNone(course_grade)
        self.assertIsNotNone(override_obj)

        api.clear_user_course_grades(wrong_user.id, self.course.id)

        after_clear_override_obj = api.get_subsection_grade_override(
            self.user.id,
            self.course.id,
            self.subsection.location
        )
        after_clear_course_grade = PersistentCourseGrade.read(self.user.id, self.course.id)
        self.assertIsNotNone(after_clear_override_obj)
        self.assertIsNotNone(after_clear_course_grade)

    @patch('lms.djangoapps.grades.models_api._PersistentSubsectionGrade')
    @patch('lms.djangoapps.grades.models_api._PersistentCourseGrade')
    @patch('lms.djangoapps.grades.models_api._PersistentSubsectionGradeOverride')
    def test_assert_clear_grade_methods_called(self, mock_override, mock_course_grade, mock_subsection_grade):
        api.clear_user_course_grades(self.user.id, self.course.id)
        mock_override.clear_override.assert_called_with(self.user.id, self.course.id)
        mock_course_grade.clear_grade.assert_called_with(self.course.id, self.user.id)
        mock_subsection_grade.clear_grade.assert_called_with(self.user.id, self.course.id)

    @patch('lms.djangoapps.grades.models_api._PersistentSubsectionGrade')
    @patch('lms.djangoapps.grades.models_api._PersistentCourseGrade')
    def test_assert_clear_grade_exception(self, mock_course_grade, mock_subsection_grade):
        with patch(
            'lms.djangoapps.grades.models_api._PersistentSubsectionGradeOverride',
            Mock(side_effect=Exception)
        ) as mock_override:
            api.clear_user_course_grades(self.user.id, self.course.id)
            self.assertRaises(Exception, mock_override)
            self.assertFalse(mock_course_grade.called)
            self.assertFalse(mock_subsection_grade.called)
