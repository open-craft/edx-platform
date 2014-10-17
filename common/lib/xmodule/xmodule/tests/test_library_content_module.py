import unittest
import mock
import random
from mock import patch
from collections import namedtuple

from xmodule.library_content_module import (
    LibraryVersionReference, LibraryList,
    LibraryContentModule, LibraryContentFields)


def _pairwise(seq):
    iter1 = iter(seq)
    iter2 = iter(seq)
    next(iter2)
    while True:
        yield next(iter1), next(iter2)


class MockObjectId(namedtuple('ObjectId', "object_id")):
    def __str__(self):
        return str(self.object_id)


class MockCourseLocator(namedtuple('CourseLocator', "org course run version")):
    def for_version(self, version):
        return self._replace(version=version)

    def __str__(self):
        return "{}/{}/{}".format(self.org, self.course, self.run)

    @staticmethod
    def from_string(string):
        args = string.split("/")
        return MockCourseLocator(*args, version=None)


assert str(MockCourseLocator.from_string("1/2/3")) == "1/2/3"


@patch('xmodule.library_content_module.ObjectId', MockObjectId)
@patch('xmodule.library_content_module.CourseLocator', MockCourseLocator)
class TestLibraryVersionReference(unittest.TestCase):
    def test_init_from_string_without_version(self):
        locator_string = "example/test/now"
        locator = MockCourseLocator("example", "test", "now", None)

        lvr = LibraryVersionReference(locator_string)

        self.assertEquals(lvr.library_id, locator)
        self.assertEquals(lvr.version, locator.version)
        self.assertIsNone(lvr.version)

    def test_init_from_course_locator_without_version(self):
        locator = MockCourseLocator("example", "test", "now", None)

        lvr = LibraryVersionReference(locator)

        self.assertEquals(lvr.library_id, locator)
        self.assertEquals(lvr.version, locator.version)
        self.assertIsNone(lvr.version)

    def test_init_from_course_locator_including_version(self):
        version = MockObjectId(1)
        locator = MockCourseLocator("example", "test", "now", version)
        expected_locator = locator._replace(version=None)

        lvr = LibraryVersionReference(locator)

        self.assertEquals(lvr.library_id, expected_locator)
        self.assertEquals(lvr.version, version)

    def test_init_from_course_locator_and_version(self):
        version = MockObjectId(1)
        locator = MockCourseLocator("example", "test", "now", None)

        lvr = LibraryVersionReference(locator, version)

        self.assertEquals(lvr.library_id, locator)
        self.assertEquals(lvr.version, version)

    def test_init_from_course_locator_and_matching_version(self):
        version = MockObjectId(1)
        locator = MockCourseLocator("example", "test", "now", version)
        expected_locator = locator._replace(version=None)

        lvr = LibraryVersionReference(locator, version)

        self.assertEquals(lvr.library_id, expected_locator)
        self.assertEquals(lvr.version, version)

    def test_init_throws_if_version_mismatch(self):
        version = MockObjectId(1)
        locator = MockCourseLocator("example", "test", "now", MockObjectId(2))

        with self.assertRaises(AssertionError):
            lvr = LibraryVersionReference(locator, version)

    def test_from_json(self):
        lvr = LibraryVersionReference.from_json(["example/test/now", "1"])
        expected_locator = MockCourseLocator("example", "test", "now", None)
        expected_version = MockObjectId("1")

        self.assertEquals(lvr.library_id, expected_locator)
        self.assertEquals(lvr.version, expected_version)

    def test_json_roundtrip(self):
        expected = ["test/json/now", "2"]
        result = LibraryVersionReference.from_json(expected).to_json()
        self.assertEquals(expected, result)


@patch('xmodule.library_content_module.ObjectId', MockObjectId)
@patch('xmodule.library_content_module.CourseLocator', MockCourseLocator)
class TestLibraryList(unittest.TestCase):
    def test_json_roundtrip(self):
        json_data = [
            ["example/test/now", "123"],
            ["organization/course/run", "abc"]]

        ll = LibraryList()

        #TODO:Shouldn't these be static methods, as they are not accessing self?
        self.assertEquals(ll.to_json(ll.from_json(json_data)), json_data)

    def test_from_json(self):
        json_data = [
            ["example/test/now", "123"],
            ["organization/course/run", "abc"]]
        expected = [LibraryVersionReference.from_json(a) for a in json_data]

        ll = LibraryList()

        #TODO: Shouldn't this return a LibraryList?
        self.assertEquals(ll.from_json(json_data), expected)


LCM = LibraryContentModule


@patch.object(LCM, "source_libraries", LCM.source_libraries.default)
@patch.object(LCM, "mode", LCM.mode.default)
@patch.object(LCM, "max_count", LCM.max_count.default)
@patch.object(LCM, "filters", LCM.filters.default)
@patch.object(LCM, "weight", LCM.weight.default)
@patch.object(LCM, "selected", LCM.selected.default)
@patch.object(LCM, "has_score", LCM.has_score.default)
@patch.object(LCM, "children", LCM.children.default)
class TestLibraryContentModule(unittest.TestCase):
    """
    get_score:
        self.has_score
        self._get_selected_child_blocks().get_score()["total", "score"]
        self.weight
    """

    def setUp(self):
        # Mocking out base classes of LibraryContentModule
        self._orig_bases = LibraryContentModule.__bases__
        LibraryContentModule.__bases__ = (LibraryContentFields,)
        # just making sure that tests are reproducible
        self._orig_random_state = random.getstate()
        random.seed(42)

        # more verbose than assertTrue(a.issubset(b))
        self.assert_is_subset = self.assertLessEqual

    def tearDown(self):
        random.setstate(self._orig_random_state)
        LibraryContentModule.__bases__ = self._orig_bases

    def test_max_score_is_weight(self):
        lcm = LibraryContentModule()

        for i in range(-10, 10):
            lcm.weight = i
            self.assertEquals(lcm.max_score(), lcm.weight)

    def test_get_child_descriptors_is_empty_since_it_breaks_grading(self):
        lcm = LibraryContentModule()

        self.assertEquals(lcm.get_child_descriptors(), [])

    def test_get_score_returns_none_when_doesnt_has_score_is_set(self):
        lcm = LibraryContentModule()
        lcm.has_score = False

        self.assertIsNone(lcm.get_score())

    #TODO: What to return when there are no children but has_score is set

    def _set_up_lcm_for_get_score(self):
        class MockChildBlock(namedtuple('XBlock', "block_id score total")):
            def get_score(self):
                return {"score": self.score, "total": self.total}

        class MockRuntime(object):
            def __init__(self, blocks):
                self.blocks = {block: block for block in blocks}

            def get_block(self, block):
                return self.blocks[block]

        lcm = LibraryContentModule()
        lcm.children = [
            MockChildBlock("a", 2, 2), MockChildBlock("b", 2, 3),
            MockChildBlock("c", 0, 5), MockChildBlock("d", 8, 10),
        ]
        lcm.max_count = 2
        lcm.runtime = MockRuntime(lcm.children)
        lcm.has_score = True

        return lcm

    def _calculate_score(self, lcm, selection):
        selected = [b for b in lcm.runtime.blocks if b.block_id in selection]
        correct = sum(b.score for b in selected)
        total = sum(b.total for b in selected)

        score = lcm.weight * correct / float(total)
        return score

    def _test_get_score(self, selected, weight):
        lcm = self._set_up_lcm_for_get_score()
        lcm.max_count = len(selected)
        lcm.selected = selected
        lcm.weight = weight

        result = self._calculate_score(lcm, selected)

        self.assertEquals(lcm.get_score()["score"], result)
        self.assertEquals(lcm.get_score()["total"], weight)

    def test_get_score(self):
        self._test_get_score(("a", "d"), 1)
        self._test_get_score(("a", "c", "d"), 2)
        self._test_get_score(("a", "b"), 1)
        self._test_get_score(("a", "b"), 5)
        self._test_get_score(("b"), 1.5)
        self._test_get_score(("a", "b", "c", "d"), 1.75)

    def test_get_score_total_is_always_weight(self):
        lcm = self._set_up_lcm_for_get_score()
        for weight in (1, 5, 3.5, 4, 16, 7.28):
            lcm.weight = weight
            self.assertEquals(lcm.get_score()["total"], weight)

    def _set_up_lcm(self, num_child, max_count, selected=None, mode="random"):
        assert mode in ["random", "first"]
        if selected is None:
            selected = []

        lcm = LibraryContentModule()

        MockChildBlock = namedtuple('XBlock', "block_id")
        lcm.children = [MockChildBlock(i) for i in range(num_child)]

        lcm.max_count = max_count
        lcm.selected = selected
        lcm.mode = mode

        all_block_ids = set(c.block_id for c in lcm.children)

        return lcm, all_block_ids

    def _assert_consistent_selection(self, selected, lcm, all_block_ids):
        max_elements = min(lcm.max_count, len(lcm.children))
        self.assertEqual(len(selected), max_elements)
        self.assertEqual(selected, set(lcm.selected))
        self.assert_is_subset(selected, all_block_ids)

    def test_selected_children_filled_from_children(self):
        lcm, all_block_ids = self._set_up_lcm(num_child=10, max_count=5)

        selection = lcm.selected_children()

        self._assert_consistent_selection(selection, lcm, all_block_ids)

    def test_selected_children_returns_all_from_small_pool(self):
        lcm, all_block_ids = self._set_up_lcm(num_child=4, max_count=6)

        selection = lcm.selected_children()

        self._assert_consistent_selection(selection, lcm, all_block_ids)
        self.assertEqual(selection, all_block_ids)

    def test_selected_children_fixes_selected_with_invalid_ids(self):
        lcm, all_block_ids = self._set_up_lcm(8, 5, selected=[-3, 1, 5, 9, 15])
        old_but_valid_ids = set(lcm.selected) & all_block_ids

        selection = lcm.selected_children()

        self._assert_consistent_selection(selection, lcm, all_block_ids)
        self.assert_is_subset(old_but_valid_ids, selection)

    def test_selected_children_fixes_selected_with_too_many_ids(self):
        lcm, all_block_ids = self._set_up_lcm(12, 4, selected=list(range(8)))
        orig_selected = set(lcm.selected)

        selection = lcm.selected_children()

        self._assert_consistent_selection(selection, lcm, all_block_ids)
        self.assert_is_subset(selection, set(orig_selected))

    def test_selected_children_fill_correctly_when_mode_is_first(self):
        lcm, all_block_ids = self._set_up_lcm(11, 7, [10, 9, 8], mode="first")
        orig_selected = set(lcm.selected)

        new_ids = lcm.max_count - len(orig_selected)
        new_block_ids = set(c.block_id for c in lcm.children[0:new_ids])
        expected_set = orig_selected | new_block_ids

        selection = lcm.selected_children()

        self._assert_consistent_selection(selection, lcm, all_block_ids)
        self.assert_is_subset(orig_selected, selection)
        self.assertEqual(selection, expected_set)

    def test_calling_selected_children_multiple_times_returns_same_result(self):
        lcm, all_block_ids = self._set_up_lcm(13, 7)

        selections = [lcm.selected_children() for i in range(10)]

        for selection in selections:
            self._assert_consistent_selection(selection, lcm, all_block_ids)
        for s1, s2 in _pairwise(selections):
            self.assertEquals(s1, s2)
