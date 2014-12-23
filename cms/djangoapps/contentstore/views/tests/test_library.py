"""
Unit tests for contentstore.views.library

More important high-level tests are in contentstore/tests/test_libraries.py
"""
import shutil
import tarfile

import ddt
import lxml.etree
from django.conf import settings
from paver.path import path
from tempfile import mkdtemp

from contentstore.tests.utils import AjaxEnabledTestClient, parse_json
from contentstore.views.component import get_component_templates
from extract_tar import safetar_extractall
from xmodule.contentstore.django import contentstore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import LibraryFactory, ItemFactory
from xmodule.modulestore.xml_exporter import export_library_to_xml
from xmodule.modulestore.xml_importer import import_library_from_xml
from mock import patch
from opaque_keys.edx.locator import CourseKey, LibraryLocator

LIBRARY_REST_URL = '/library/'  # URL for GET/POST requests involving libraries

TEST_DATA_DIR = settings.COMMON_TEST_DATA_ROOT


def make_url_for_lib(key):
    """ Get the RESTful/studio URL for testing the given library """
    if isinstance(key, LibraryLocator):
        key = unicode(key)
    return LIBRARY_REST_URL + key


@ddt.ddt
class UnitTestLibraries(ModuleStoreTestCase):
    """
    Unit tests for library views
    """

    def setUp(self):
        user_password = super(UnitTestLibraries, self).setUp()

        self.client = AjaxEnabledTestClient()
        self.client.login(username=self.user.username, password=user_password)

    ######################################################
    # Tests for /library/ - list and create libraries:

    @patch("contentstore.views.library.LIBRARIES_ENABLED", False)
    def test_with_libraries_disabled(self):
        """
        The library URLs should return 404 if libraries are disabled.
        """
        response = self.client.get_json(LIBRARY_REST_URL)
        self.assertEqual(response.status_code, 404)

    def test_list_libraries(self):
        """
        Test that we can GET /library/ to list all libraries visible to the current user.
        """
        # Create some more libraries
        libraries = [LibraryFactory.create() for _ in range(0, 3)]
        lib_dict = dict([(lib.location.library_key, lib) for lib in libraries])

        response = self.client.get_json(LIBRARY_REST_URL)
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

    @ddt.data("delete", "put")
    def test_bad_http_verb(self, verb):
        """
        We should get an error if we do weird requests to /library/
        """
        response = getattr(self.client, verb)(LIBRARY_REST_URL)
        self.assertEqual(response.status_code, 405)

    def test_create_library(self):
        """ Create a library. """
        response = self.client.ajax_post(LIBRARY_REST_URL, {
            'org': 'org',
            'library': 'lib',
            'display_name': "New Library",
        })
        self.assertEqual(response.status_code, 200)
        # That's all we check. More detailed tests are in contentstore.tests.test_libraries...

    @patch.dict('django.conf.settings.FEATURES', {'ENABLE_CREATOR_GROUP': True})
    def test_lib_create_permission(self):
        """
        Users who aren't given course creator roles shouldn't be able to create
        libraries either.
        """
        self.client.logout()
        ns_user, password = self.create_non_staff_user()
        self.client.login(username=ns_user.username, password=password)

        response = self.client.ajax_post(LIBRARY_REST_URL, {
            'org': 'org', 'library': 'lib', 'display_name': "New Library",
        })
        self.assertEqual(response.status_code, 403)

    @ddt.data(
        {},
        {'org': 'org'},
        {'library': 'lib'},
        {'org': 'C++', 'library': 'lib', 'display_name': 'Lib with invalid characters in key'},
        {'org': 'Org', 'library': 'Wh@t?', 'display_name': 'Lib with invalid characters in key'},
    )
    def test_create_library_invalid(self, data):
        """
        Make sure we are prevented from creating libraries with invalid keys/data
        """
        response = self.client.ajax_post(LIBRARY_REST_URL, data)
        self.assertEqual(response.status_code, 400)

    def test_no_duplicate_libraries(self):
        """
        We should not be able to create multiple libraries with the same key
        """
        lib = LibraryFactory.create()
        lib_key = lib.location.library_key
        response = self.client.ajax_post(LIBRARY_REST_URL, {
            'org': lib_key.org,
            'library': lib_key.library,
            'display_name': "A Duplicate key, same as 'lib'",
        })
        self.assertIn('already a library defined', parse_json(response)['ErrMsg'])
        self.assertEqual(response.status_code, 400)

    ######################################################
    # Tests for /library/:lib_key/ - get a specific library as JSON or HTML editing view

    def test_get_lib_info(self):
        """
        Test that we can get data about a library (in JSON format) using /library/:key/
        """
        # Create a library
        lib_key = LibraryFactory.create().location.library_key
        # Re-load the library from the modulestore, explicitly including version information:
        lib = self.store.get_library(lib_key, remove_version=False, remove_branch=False)
        version = lib.location.library_key.version_guid
        self.assertNotEqual(version, None)

        response = self.client.get_json(make_url_for_lib(lib_key))
        self.assertEqual(response.status_code, 200)
        info = parse_json(response)
        self.assertEqual(info['display_name'], lib.display_name)
        self.assertEqual(info['library_id'], unicode(lib_key))
        self.assertEqual(info['previous_version'], None)
        self.assertNotEqual(info['version'], None)
        self.assertNotEqual(info['version'], '')
        self.assertEqual(info['version'], unicode(version))

    def test_get_lib_edit_html(self):
        """
        Test that we can get the studio view for editing a library using /library/:key/
        """
        lib = LibraryFactory.create()

        response = self.client.get(make_url_for_lib(lib.location.library_key))
        self.assertEqual(response.status_code, 200)
        self.assertIn("<html", response.content)
        self.assertIn(lib.display_name, response.content)

    @ddt.data('library-v1:Nonexistent+library', 'course-v1:Org+Course', 'course-v1:Org+Course+Run', 'invalid')
    def test_invalid_keys(self, key_str):
        """
        Check that various Nonexistent/invalid keys give 404 errors
        """
        response = self.client.get_json(make_url_for_lib(key_str))
        self.assertEqual(response.status_code, 404)

    def test_bad_http_verb_with_lib_key(self):
        """
        We should get an error if we do weird requests to /library/
        """
        lib = LibraryFactory.create()
        for verb in ("post", "delete", "put"):
            response = getattr(self.client, verb)(make_url_for_lib(lib.location.library_key))
            self.assertEqual(response.status_code, 405)

    def test_no_access(self):
        user, password = self.create_non_staff_user()
        self.client.login(username=user, password=password)

        lib = LibraryFactory.create()
        response = self.client.get(make_url_for_lib(lib.location.library_key))
        self.assertEqual(response.status_code, 403)

    def test_get_component_templates(self):
        """
        Verify that templates for adding discussion and advanced components to
        content libraries are not provided.
        """
        lib = LibraryFactory.create()
        lib.advanced_modules = ['lti']
        lib.save()
        templates = [template['type'] for template in get_component_templates(lib, library=True)]
        self.assertIn('problem', templates)
        self.assertNotIn('discussion', templates)
        self.assertNotIn('advanced', templates)

    def test_library_export(self):
        """
        Verify that useable library data can be exported.
        """
        youtube_id = "qS4NO9MNC6w"
        library = LibraryFactory.create(modulestore=self.store)
        video_block = ItemFactory.create(
            category="video",
            parent_location=library.location,
            user_id=self.user.id,
            publish_item=False,
            youtube_id_1_0=youtube_id
        )
        name = library.url_name
        lib_key = library.location.library_key
        root_dir = path(mkdtemp())
        try:
            export_library_to_xml(self.store, contentstore(), lib_key, root_dir, name)
            lib_xml = lxml.etree.XML(open(root_dir / name / 'library.xml').read())
            self.assertEqual(lib_xml.get('org'), lib_key.org)
            self.assertEqual(lib_xml.get('library'), lib_key.library)
            block = lib_xml.find('video')
            self.assertIsNotNone(block)
            self.assertEqual(block.get('url_name'), video_block.url_name)
            video_xml = lxml.etree.XML(open(root_dir / name / 'video' / video_block.url_name + '.xml').read())
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
        library = LibraryFactory.create(modulestore=self.store)
        lib_key = library.location.library_key
        test_block = ItemFactory.create(
            category="vertical",
            parent_location=library.location,
            user_id=self.user.id,
            publish_item=False,
        )
        test_block2 = ItemFactory.create(
            category="vertical",
            parent_location=library.location,
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
        # Refresh library.
        library = self.store.get_library(lib_key)
        children = [self.store.get_item(child).url_name for child in library.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block.url_name, children)
        self.assertIn(test_block2.url_name, children)

        unchanged_lib = self.store.get_library(unchanged_key)
        children = [self.store.get_item(child).url_name for child in unchanged_lib.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block3.url_name, children)
        self.assertIn(test_block4.url_name, children)

        extract_dir = path(mkdtemp())
        try:
            tar = tarfile.open(path(TEST_DATA_DIR) / 'library_import' / 'library.HhJfPD.tar.gz')
            safetar_extractall(tar, extract_dir)
            library_items = import_library_from_xml(
                self.store, self.user.id,
                settings.GITHUB_REPO_ROOT, [extract_dir / 'library'],
                load_error_modules=False,
                static_content_store=contentstore(),
                target_library_id=lib_key
            )
        finally:
            shutil.rmtree(extract_dir)

        self.assertEqual(lib_key, library_items[0].location.library_key)
        library = self.store.get_library(lib_key)
        children = [self.store.get_item(child).url_name for child in library.children]
        self.assertEqual(len(children), 3)
        self.assertNotIn(test_block.url_name, children)
        self.assertNotIn(test_block2.url_name, children)

        unchanged_lib = self.store.get_library(unchanged_key)
        children = [self.store.get_item(child).url_name for child in unchanged_lib.children]
        self.assertEqual(len(children), 2)
        self.assertIn(test_block3.url_name, children)
        self.assertIn(test_block4.url_name, children)
