"""
Content library unit tests that require the CMS runtime.
"""
from django.conf import settings
from lxml import etree
from paver.path import path
import shutil
import tarfile
from tempfile import NamedTemporaryFile, mkdtemp
from contentstore.tests.utils import AjaxEnabledTestClient, parse_json
from contentstore.utils import reverse_usage_url
from contentstore.views.tests.test_library import LIBRARY_REST_URL
from fs.memoryfs import MemoryFS
from extract_tar import safetar_extractall
from xmodule.contentstore.django import contentstore
from xmodule.library_content_module import LibraryVersionReference
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import LibraryFactory, CourseFactory, ItemFactory
from xmodule.modulestore.xml_exporter import export_library_to_xml
from xmodule.modulestore.xml_importer import import_library_from_xml
from xmodule.tests import get_test_system
from mock import Mock
from opaque_keys.edx.locator import CourseKey, LibraryLocator
import ddt


TEST_DATA_DIR = settings.COMMON_TEST_DATA_ROOT


class TestLibraryMixin(ModuleStoreTestCase):
    def setUp(self):
        user_password = super(TestLibraryMixin, self).setUp()

        self.client = AjaxEnabledTestClient()
        self.client.login(username=self.user.username, password=user_password)

        self.lib_key = self._create_library()
        self.library = modulestore().get_library(self.lib_key)

    def _create_module_system(self, course):
        """
        Create an xmodule system so we can use bind_for_student
        """
        def get_module(descriptor):
            """Mocks module_system get_module function"""
            module_system = get_test_system()
            module_system.get_module = get_module
            descriptor.bind_for_student(module_system, descriptor._field_data)  # pylint: disable=protected-access
            return descriptor

        module_system = get_test_system()
        module_system.get_module = get_module
        module_system.descriptor_system = course.runtime
        course.runtime.export_fs = MemoryFS()
        return module_system

    def _create_library(self, org="org", library="lib", display_name="Test Library"):
        """
        Helper method used to create a library. Uses the REST API.
        """
        response = self.client.ajax_post(LIBRARY_REST_URL, {
            'org': org,
            'library': library,
            'display_name': display_name,
            })
        self.assertEqual(response.status_code, 200)
        lib_info = parse_json(response)
        lib_key = CourseKey.from_string(lib_info['library_key'])
        self.assertIsInstance(lib_key, LibraryLocator)
        return lib_key

    def _add_library_content_block(self, course, library_key, other_settings=None):
        """
        Helper method to add a LibraryContent block to a course.
        The block will be configured to select content from the library
        specified by library_key.
        other_settings can be a dict of Scope.settings fields to set on the block.
        """
        metadata = {'source_libraries': [LibraryVersionReference(library_key)]}
        if other_settings:
            metadata.update(other_settings)
        return ItemFactory.create(
            category='library_content',
            parent_location=course.location,
            user_id=self.user.id,
            metadata=metadata,
            publish_item=False,
            )

    def _refresh_children(self, lib_content_block):
        """
        Helper method: Uses the REST API to call the 'refresh_children' handler
        of a LibraryContent block
        """
        if 'user' not in lib_content_block.runtime._services:  # pylint: disable=protected-access
            lib_content_block.runtime._services['user'] = Mock(user_id=self.user.id)  # pylint: disable=protected-access
        handler_url = reverse_usage_url('component_handler', lib_content_block.location, kwargs={'handler': 'refresh_children'})
        response = self.client.ajax_post(handler_url)
        self.assertEqual(response.status_code, 200)
        return modulestore().get_item(lib_content_block.location)


@ddt.ddt
class TestLibraries(TestLibraryMixin):
    """
    High-level tests for libraries
    """

    def test_list_libraries(self):
        """
        Test that we can GET /library/ to list all libraries visible to the current user.
        """
        list_url = '/library/'
        # Create some more libraries
        libraries = [LibraryFactory.create() for _ in range(0, 3)]
        libraries.append(self.library)
        lib_dict = dict([(lib.location.library_key, lib) for lib in libraries])

        response = self.client.get_json(list_url)
        self.assertEqual(response.status_code, 200)
        lib_list = parse_json(response)
        self.assertEqual(len(lib_list), len(libraries))
        for entry in lib_list:
            self.assertIn("library_key", entry)
            self.assertIn("display_name", entry)
            key = CourseKey.from_string(entry["library_key"])
            self.assertIn(key, lib_dict)
            self.assertEqual(entry["display_name"], lib_dict[key].display_name)
            del lib_dict[key]  # To ensure no duplicates are matched

    def test_no_duplicate_libraries(self):
        response = self.client.ajax_post('/library/', {
            'org': self.lib_key.org,
            'library': self.lib_key.library,
            'display_name': "A Duplicate key, same as self.library",
        })
        self.assertIn('duplicate', parse_json(response)['ErrMsg'])
        self.assertEqual(response.status_code, 400)

    @ddt.data(
        (2, 1, 1),
        (2, 2, 2),
        (2, 20, 2),
    )
    @ddt.unpack
    def test_max_items(self, num_to_create, num_to_select, num_expected):
        """
        Test the 'max_count' property of LibraryContent blocks.
        """
        for _ in range(0, num_to_create):
            ItemFactory.create(category="html", parent_location=self.library.location, user_id=self.user.id, publish_item=False)

        with modulestore().default_store(ModuleStoreEnum.Type.split):
            course = CourseFactory.create()

        lc_block = self._add_library_content_block(course, self.lib_key, {'max_count': num_to_select})
        self.assertEqual(len(lc_block.children), 0)
        lc_block = self._refresh_children(lc_block)

        # Now, we want to make sure that .children has the total # of potential
        # children, and that get_child_descriptors() returns the actual children
        # chosen for a given student.
        # In order to be able to call get_child_descriptors(), we must first
        # call bind_for_student:
        lc_block.bind_for_student(self._create_module_system(course), lc_block._field_data)  # pylint: disable=protected-access
        self.assertEqual(len(lc_block.children), num_to_create)
        self.assertEqual(len(lc_block.get_child_descriptors()), num_expected)

    def test_consistent_children(self):
        """
        Test that the same student will always see the same selected child block
        """
        # Create many blocks in the library and add them to a course:
        for num in range(0, 8):
            ItemFactory.create(
                metadata={"data": "This is #{}".format(num + 1)},
                category="html", parent_location=self.library.location, user_id=self.user.id, publish_item=False
            )

        with modulestore().default_store(ModuleStoreEnum.Type.split):
            course = CourseFactory.create()
            module_system = self._create_module_system(course)

        lc_block = self._add_library_content_block(course, self.lib_key, {'max_count': 1})
        lc_block_key = lc_block.location
        lc_block = self._refresh_children(lc_block)

        def get_child_of_lc_block(block):
            """
            Helper that gets the actual child block seen by a student.
            We cannot use get_child_descriptors because it uses features that
            are mocked by the test runtime.
            """
            block_ids = list(block._xmodule.selected_children())  # pylint: disable=protected-access
            self.assertEqual(len(block_ids), 1)
            for child_key in block.children:
                if child_key.block_id == block_ids[0]:
                    return modulestore().get_item(child_key)

        # bind the module for a student:
        lc_block.bind_for_student(module_system, lc_block._field_data)  # pylint: disable=protected-access
        chosen_child = get_child_of_lc_block(lc_block)
        chosen_child_defn_id = chosen_child.definition_locator.definition_id

        modulestore().update_item(lc_block, self.user.id)

        # Now re-load the block and try again:
        def check():
            """
            Confirm that chosen_child is still the child seen by the test student
            """
            for _ in range(0, 10):  # Repeat many times b/c blocks are randomized
                lc_block = modulestore().get_item(lc_block_key)  # Reload block from the database
                lc_block.bind_for_student(module_system, lc_block._field_data)  # pylint: disable=protected-access
                current_child = get_child_of_lc_block(lc_block)
                self.assertEqual(current_child.location, chosen_child.location)
                self.assertEqual(current_child.data, chosen_child.data)
                self.assertEqual(current_child.definition_locator.definition_id, chosen_child_defn_id)
        check()

        # Refresh the children:
        lc_block = self._refresh_children(lc_block)
        lc_block.bind_for_student(module_system, lc_block._field_data)  # pylint: disable=protected-access

        # Now re-load the block and try yet again, in case refreshing the children changed anything:
        check()

    def test_definition_shared_with_library(self):
        """
        Test that the same block definition is used for the library and course[s]
        """
        block1 = ItemFactory.create(category="html", parent_location=self.library.location, user_id=self.user.id, publish_item=False)
        def_id1 = block1.definition_locator.definition_id
        block2 = ItemFactory.create(category="html", parent_location=self.library.location, user_id=self.user.id, publish_item=False)
        def_id2 = block2.definition_locator.definition_id
        self.assertNotEqual(def_id1, def_id2)

        # Next, create a course:
        with modulestore().default_store(ModuleStoreEnum.Type.split):
            course = CourseFactory.create()

        # Add a LibraryContent block to the course:
        lc_block = self._add_library_content_block(course, self.lib_key)
        lc_block = self._refresh_children(lc_block)
        for child_key in lc_block.children:
            child = modulestore().get_item(child_key)
            def_id = child.definition_locator.definition_id
            self.assertIn(def_id, (def_id1, def_id2))

    def test_fields(self):
        """
        Test that blocks used from a library have the same field values as
        defined by the library author.
        """
        data_value = "A Scope.content value"
        name_value = "A Scope.settings value"
        lib_block = ItemFactory.create(
            category="html",
            parent_location=self.library.location,
            user_id=self.user.id,
            publish_item=False,
            display_name=name_value,
            metadata={
                "data": data_value,
            },
        )
        self.assertEqual(lib_block.data, data_value)
        self.assertEqual(lib_block.display_name, name_value)

        # Next, create a course:
        with modulestore().default_store(ModuleStoreEnum.Type.split):
            course = CourseFactory.create()

        # Add a LibraryContent block to the course:
        lc_block = self._add_library_content_block(course, self.lib_key)
        lc_block = self._refresh_children(lc_block)
        course_block = modulestore().get_item(lc_block.children[0])

        self.assertEqual(course_block.data, data_value)
        self.assertEqual(course_block.display_name, name_value)

    def test_block_with_children(self):
        """
        Test that blocks used from a library can have children.
        """
        data_value = "A Scope.content value"
        name_value = "A Scope.settings value"
        # In the library, create a vertical block with a child:
        vert_block = ItemFactory.create(
            category="vertical",
            parent_location=self.library.location,
            user_id=self.user.id,
            publish_item=False,
        )
        child_block = ItemFactory.create(
            category="html",
            parent_location=vert_block.location,
            user_id=self.user.id,
            publish_item=False,
            display_name=name_value,
            metadata={"data": data_value, },
        )
        self.assertEqual(child_block.data, data_value)
        self.assertEqual(child_block.display_name, name_value)

        # Next, create a course:
        with modulestore().default_store(ModuleStoreEnum.Type.split):
            course = CourseFactory.create()

        # Add a LibraryContent block to the course:
        lc_block = self._add_library_content_block(course, self.lib_key)
        lc_block = self._refresh_children(lc_block)
        self.assertEqual(len(lc_block.children), 1)
        course_vert_block = modulestore().get_item(lc_block.children[0])
        self.assertEqual(len(course_vert_block.children), 1)
        course_child_block = modulestore().get_item(course_vert_block.children[0])

        self.assertEqual(course_child_block.data, data_value)
        self.assertEqual(course_child_block.display_name, name_value)


class TestLibraryImportExport(TestLibraryMixin):
    """
    Test import and export of libraries.

    Note: At the moment there are no tests for static content because
    it is unclear how or if it would be used in libraries. When this is
    resolved, tests for the static content import/export should be added.
    """
    def test_library_export(self):
        """
        Verify that useable library data can be exported.
        """
        youtube_id = "qS4NO9MNC6w"
        video_block = ItemFactory.create(
            category="video",
            parent_location=self.library.location,
            user_id=self.user.id,
            publish_item=False,
            youtube_id_1_0=youtube_id
        )
        name = self.library.url_name
        root_dir = path(mkdtemp())
        try:
            export_library_to_xml(modulestore(), contentstore(), self.lib_key, root_dir, name)
            lib_xml = etree.XML(open(root_dir / name / 'library.xml').read())
            self.assertEqual(lib_xml.get('org'), self.lib_key.org)
            self.assertEqual(lib_xml.get('library'), self.lib_key.library)
            block = lib_xml.find('video')
            self.assertIsNotNone(block)
            self.assertEqual(block.get('url_name'), video_block.url_name)
            video_xml = etree.XML(open(root_dir / name / 'video' / video_block.url_name + '.xml').read())
            self.assertEqual(video_xml.tag, 'video')
            self.assertEqual(video_xml.get('youtube_id_1_0'), youtube_id)
        finally:
            shutil.rmtree(root_dir / name)

    def test_library_import(self):
        """
        Try importing a known good library archive, and verify that the
        contents of the library have completely replaced the old contents.
        """
        # Create some blocks to overwrite
        test_block = ItemFactory.create(
            category="vertical",
            parent_location=self.library.location,
            user_id=self.user.id,
            publish_item=False,
        )
        test_block2 = ItemFactory.create(
            category="vertical",
            parent_location=self.library.location,
            user_id=self.user.id,
            publish_item=False
        )
        # Create a library and blocks that should remain unmolested.
        unchanged_lib = LibraryFactory.create()
        unchanged_key = unchanged_lib.location.library_key
        test_block3 = ItemFactory.create(
            category="vertical",
            parent_location=unchanged_lib.location,
            user_id=self.user.id,
            publish_item=False
        )
        test_block4 = ItemFactory.create(
            category="vertical",
            parent_location=unchanged_lib.location,
            user_id=self.user.id,
            publish_item=False
        )
        # Verify these blocks are in the library.
        store = modulestore()
        # Refresh library.
        library = store.get_library(self.lib_key)
        children = [store.get_item(child).url_name for child in library.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block.url_name, children)
        self.assertIn(test_block2.url_name, children)

        unchanged_lib = store.get_library(unchanged_key)
        children = [store.get_item(child).url_name for child in unchanged_lib.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block3.url_name, children)
        self.assertIn(test_block4.url_name, children)

        extract_dir = path(mkdtemp())
        try:
            tar = tarfile.open(path(TEST_DATA_DIR) / 'library_import' / 'library.HhJfPD.tar.gz')
            safetar_extractall(tar, extract_dir)
            library_items = import_library_from_xml(
                store, self.user.id,
                settings.GITHUB_REPO_ROOT, [extract_dir / 'library'],
                load_error_modules=False,
                static_content_store=contentstore(),
                target_library_id=self.lib_key
            )
        finally:
            shutil.rmtree(extract_dir)

        self.assertEqual(library, library_items[0])
        library = store.get_library(self.lib_key)
        children = [store.get_item(child).url_name for child in library.children]
        self.assertEqual(len(children), 3)
        self.assertNotIn(test_block.url_name, children)
        self.assertNotIn(test_block2.url_name, children)

        unchanged_lib = store.get_library(unchanged_key)
        children = [store.get_item(child).url_name for child in unchanged_lib.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block3.url_name, children)
        self.assertIn(test_block4.url_name, children)