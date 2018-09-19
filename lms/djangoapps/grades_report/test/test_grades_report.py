"""
Test for grade services
"""
from lms.djangoapps.grades_report.grade_services import (
    GradeServices,
    BySectionGradeServices,
    EnhancedProblemGradeServices,
)
from lms.djangoapps.grades_report.test.test_course import CourseTest


class GradeServicesTest(CourseTest):
    """
    Test the class that calculates grades for additional report.
    """
    @classmethod
    def setUpClass(cls):
        super(GradeServicesTest, cls).setUpClass()
        cls.grade_services = GradeServices(cls.course.id.html_id())
        cls.by_section_grades_services = BySectionGradeServices(cls.course.id.html_id())
        cls.enhanced_problem_grades_services = EnhancedProblemGradeServices(cls.course.id.html_id())


    def test_total_percent_by_section(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        total_by_section = sum(x['percent'] for x in grades_by_section['data'][0]['section_at_breakdown'])
        self.assertAlmostEqual(grades_by_section['data'][0]['percent'], total_by_section)


    def test_max_possible_percent_total(self):
        MAX_POSSIBLE_PERCENT_PER_COURSE = 1.00
        grades_by_section = self.grade_services.get_grades_by_section()
        max_possible_percent_total = sum(x['max_possible_percent'] for x in grades_by_section['data'][0]['section_at_breakdown'])
        self.assertAlmostEqual(max_possible_percent_total, MAX_POSSIBLE_PERCENT_PER_COURSE)


    def test_by_section_report_keys(self):
        by_section_data = self.by_section_grades_services.by_section()
        self.assertNotIn('section_at_breakdown', by_section_data[0])
        self.assertIn('up_to_date_grade', by_section_data[0])


    def test_enhanced_problem_grade(self):
        problem_grade_report = self.enhanced_problem_grades_services.enhanced_problem_grade()
        self.assertIn('problem_breakdown', problem_grade_report[0])


    def test_up_to_date_grade_in_all_sections(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        self.assertIn('up_to_date_grade', grades_by_section['data'][0])
        up_to_date_grade_percent = grades_by_section['data'][0]['up_to_date_grade']['percent']
        total_percent = grades_by_section['data'][0]['percent']
        self.assertEquals(up_to_date_grade_percent, total_percent)


    def test_up_to_date_grade_till_a_section(self):
        # Send 'a' as section_block_id parameter, what's mean the first section in our course
        grades_by_section = self.grade_services.get_grades_by_section('a')
        self.assertIn('up_to_date_grade', grades_by_section['data'][0])
        up_to_date_grade_percent = grades_by_section['data'][0]['up_to_date_grade']['percent']
        total_percent = grades_by_section['data'][0]['percent']
        self.assertNotEquals(up_to_date_grade_percent, total_percent)


    def test_important_keys_in_section_filtered(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        for item in grades_by_section['data'][0]['section_filtered']:
            self.assertIn('section_block_id', item)
            self.assertIsNotNone(item['section_block_id'])
        for item in grades_by_section['data'][0]['section_filtered']:
            self.assertIn('section_display_name', item)
            self.assertIsNotNone(item['section_display_name'])


    def test_calculated_up_to_date_grade(self):
        grades_by_section = self.grade_services.get_grades_by_section('a')
        # up-to-date-percent calculated up to section 'a'.
        EXPECTED_UP_TO_DATE_GRADE_PERCENT = 0.958333333
        up_to_date_grade_percent = grades_by_section['data'][0]['up_to_date_grade']['percent']
        up_to_date_grade_section = grades_by_section['data'][0]['up_to_date_grade']['calculated_until_section']
        self.assertEquals(up_to_date_grade_section, 'a')
        self.assertAlmostEqual(up_to_date_grade_percent, EXPECTED_UP_TO_DATE_GRADE_PERCENT)


    def test_total_sections_dropped(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        TOTAL_DROPPED_SECTIONS = 4
        dropped_sections = list(x for x in grades_by_section['data'][0]['section_breakdown'] if 'mark' in x)
        self.assertEquals(len(dropped_sections), TOTAL_DROPPED_SECTIONS)


    def test_total_sections_unreleased(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        TOTAL_UNRELEASED_SECTIONS = 5
        section_filtered = grades_by_section['data'][0]['section_filtered']
        dropped_sections = list(x for x in section_filtered if 'Unreleased' in x['section_block_id'])
        self.assertEquals(len(dropped_sections), TOTAL_UNRELEASED_SECTIONS)


    def test_total_assignment_types_per_section(self):
        grades_by_section = self.grade_services.get_grades_by_section()
        section_breakdown = grades_by_section['data'][0]['section_at_breakdown']
        # In the first section must be exist just one assignment type: Homework.
        self.assertEquals(len(section_breakdown[0]['assignment_types']), 1)
        # In the second section must be exist two assignment types: Exams and Lab.
        self.assertEquals(len(section_breakdown[1]['assignment_types']), 2)
        # In the third section must be exist three assignment types: Homework, Exams and Quiz.
        self.assertEquals(len(section_breakdown[2]['assignment_types']), 3)
