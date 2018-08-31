"""
Course for test
"""
from lms.djangoapps.grades.tests.utils import answer_problem
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from openedx.core.djangolib.testing.utils import get_mock_request
from student.models import CourseEnrollment
from student.tests.factories import AdminFactory, CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory


class CourseTest(SharedModuleStoreTestCase):
    """
    Test the class that calculates grades for additional report.
    This test class uses a course hierarchy described as follows:
                                                a                        o
                                       +--------+--------+          +----+----+
                                       b                 c          p         q
                        +--------------+-----------+     |          |         |
                        d              e           f     g          r         s
                     +-----+     +-----+-----+     |     |          |         |
                     h     i     j     k     l     m     n          t         u
                  (15/15)(5/5) (0/1)   -   (3/3)   -   (0/10)     (8/20)   (20/25)
    """
    @classmethod
    def setUpClass(cls):
        super(CourseTest, cls).setUpClass()
        cls.grading_policy = {
            "GRADER": [
                {
                    "type": "Homework",
                    "min_count": 5,
                    "drop_count": 1,
                    "short_label": "HW",
                    "weight": 0.2,
                },
                {
                    "type": "Lab",
                    "min_count": 2,
                    "drop_count": 1,
                    "short_label": "LB",
                    "weight": 0.5,
                },
                {
                    "type": "Exams",
                    "min_count": 2,
                    "drop_count": 0,
                    "short_label": "EX",
                    "weight": 0.2,
                },
                {
                    "type": "SomeOther",
                    "min_count": 3,
                    "drop_count": 1,
                    "short_label": "SO",
                    "weight": 0.1,
                },
            ],
            "GRADE_CUTOFFS": {
                "Pass": 0.5,
            },
        }
        cls.course = CourseFactory.create()
        cls.course.set_grading_policy(cls.grading_policy)
        with cls.store.bulk_operations(cls.course.id):
            cls.a = ItemFactory.create(parent=cls.course, category="chapter", display_name="a")
            cls.b = ItemFactory.create(parent=cls.a, category="sequential", display_name="b", format="Homework", graded=True)
            cls.c = ItemFactory.create(parent=cls.a, category="sequential", display_name="c", format="Lab", graded=True)
            cls.d = ItemFactory.create(parent=cls.b, category="vertical", display_name="d")
            cls.e = ItemFactory.create(parent=cls.b, category="vertical", display_name="e")
            cls.f = ItemFactory.create(parent=cls.b, category="vertical", display_name="f")
            cls.g = ItemFactory.create(parent=cls.c, category="vertical", display_name="g")
            cls.h = ItemFactory.create(parent=cls.d, category="problem", display_name="h")
            cls.i = ItemFactory.create(parent=cls.d, category="problem", display_name="i")
            cls.j = ItemFactory.create(parent=cls.e, category="problem", display_name="j")
            cls.k = ItemFactory.create(parent=cls.e, category="html", display_name="k")
            cls.l = ItemFactory.create(parent=cls.e, category="problem", display_name="l")
            cls.m = ItemFactory.create(parent=cls.f, category="html", display_name="m")
            cls.n = ItemFactory.create(parent=cls.g, category="problem", display_name="n")
            cls.o = ItemFactory.create(parent=cls.course, category="chapter", display_name="o")
            cls.p = ItemFactory.create(parent=cls.o, category="sequential", display_name="p", format="Lab", graded=True)
            cls.q = ItemFactory.create(parent=cls.o, category="sequential", display_name="q", format="Exams", graded=True)
            cls.r = ItemFactory.create(parent=cls.p, category="vertical", display_name="r")
            cls.s = ItemFactory.create(parent=cls.q, category="vertical", display_name="s")
            cls.t = ItemFactory.create(parent=cls.r, category="problem", display_name="t")
            cls.u = ItemFactory.create(parent=cls.s, category="problem", display_name="u")


        cls.request = get_mock_request(UserFactory())
        CourseEnrollment.enroll(cls.request.user, cls.course.id)

        answer_problem(cls.course, cls.request, cls.h, score=15, max_value=15)
        answer_problem(cls.course, cls.request, cls.i, score=5, max_value=5)
        answer_problem(cls.course, cls.request, cls.j, score=0, max_value=1)
        answer_problem(cls.course, cls.request, cls.l, score=3, max_value=3)
        answer_problem(cls.course, cls.request, cls.n, score=0, max_value=10)
        answer_problem(cls.course, cls.request, cls.t, score=8, max_value=20)
        answer_problem(cls.course, cls.request, cls.u, score=20, max_value=25)

        cls.course_grade = CourseGradeFactory().create(cls.request.user, cls.course)
