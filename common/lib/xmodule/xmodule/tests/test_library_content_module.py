import unittest
import mock
from collections import namedtuple


from xmodule.library_content_module import LibraryVersionReference


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


@mock.patch('xmodule.library_content_module.ObjectId', MockObjectId)
@mock.patch('xmodule.library_content_module.CourseLocator', MockCourseLocator)
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
