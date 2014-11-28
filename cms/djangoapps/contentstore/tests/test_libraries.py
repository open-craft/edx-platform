"""
Content library unit tests that require the CMS runtime.
"""
from contentstore.tests.utils import AjaxEnabledTestClient, parse_json
from contentstore.utils import reverse_url, reverse_usage_url, reverse_library_url
from contentstore.views.access import has_read_access, has_write_access
from contentstore.views.tests.test_library import LIBRARY_REST_URL
from fs.memoryfs import MemoryFS
from student.roles import (
    CourseInstructorRole, CourseStaffRole, CourseCreatorRole, LibraryUserRole,
    OrgStaffRole, OrgInstructorRole, OrgLibraryUserRole,
)
from xmodule.library_content_module import LibraryVersionReference
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.tests import get_test_system
from mock import Mock, patch
from opaque_keys.edx.locator import CourseKey, LibraryLocator
import ddt

LIBRARY_REST_URL = '/library/'  # URL for GET/POST requests involving libraries themselves


class LibraryTestCase(ModuleStoreTestCase):
    """
    Common functionality for content libraries tests
    """
    def setUp(self):
        user_password = super(LibraryTestCase, self).setUp()

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

    def _list_libraries(self):
        """
        Use the REST API to get a list of libraries visible to the current user.
        """
        response = self.client.get_json(LIBRARY_REST_URL)
        self.assertEqual(response.status_code, 200)
        return parse_json(response)

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
class TestLibraries(LibraryTestCase):
    """
    High-level tests for libraries
    """

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


@ddt.ddt
class TestLibraryAccess(LibraryTestCase):
    """
    Test Roles and Permissions related to Content Libraries
    """
    def setUp(self):
        """ Create a library, staff user, and non-staff user """
        super(TestLibraryAccess, self).setUp()
        self.ns_user, self.ns_user_password = self.create_non_staff_user()

    def _login_as_non_staff_user(self, logout_first=True):
        """ Login as a user that starts out with no roles/permissions granted. """
        if logout_first:
            self.client.logout()  # We start logged in as a staff user
        self.client.login(username=self.ns_user.username, password=self.ns_user_password)

    def _assert_cannot_create_library(self, org="org", library="libfail", expected_code=403):
        """ Ensure the current user is not able to create a library. """
        self.assertTrue(expected_code >= 300)
        response = self.client.ajax_post(LIBRARY_REST_URL, {'org': org, 'library': library, 'display_name': "Irrelevant"})
        self.assertEqual(response.status_code, expected_code)
        key = LibraryLocator(org=org, library=library)
        self.assertEqual(modulestore().get_library(key), None)

    def _can_access_library(self, lib_key):
        """ Use the normal studio library URL to check if we have access """
        if not isinstance(lib_key, (basestring, LibraryLocator)):
            lib_key = lib_key.location.library_key
        response = self.client.get(reverse_library_url('library_handler', unicode(lib_key)))
        self.assertIn(response.status_code, (200, 302, 403))
        return response.status_code == 200

    def tearDown(self):
        """
        Log out when done each test
        """
        self.client.logout()
        super(TestLibraryAccess, self).tearDown()

    def test_creation(self):
        """
        The user that creates a library should have instructor (admin) and staff permissions
        """
        # self.library has been auto-created by the staff user.
        self.assertTrue(has_write_access(self.user, self.lib_key))
        self.assertTrue(has_read_access(self.user, self.lib_key))
        # Make sure the user was actually assigned the instructor role and not just using is_staff superpowers:
        self.assertTrue(CourseInstructorRole(self.lib_key).has_user(self.user))

        # Now log out and ensure we are forbidden from creating a library:
        self.client.logout()
        self._assert_cannot_create_library(expected_code=302)  # 302 redirect to login expected

        # Now create a non-staff user with no permissions:
        self._login_as_non_staff_user(logout_first=False)
        self.assertFalse(CourseCreatorRole().has_user(self.ns_user))

        # Now check that logged-in users without any permissions cannot create libraries
        with patch.dict('django.conf.settings.FEATURES', {'ENABLE_CREATOR_GROUP': True}):
            self._assert_cannot_create_library()

    @ddt.data(
        CourseInstructorRole,
        CourseStaffRole,
        LibraryUserRole,
    )
    def test_acccess(self, access_role):
        """
        Test the various roles that allow viewing libraries are working correctly.
        """
        # At this point, one library exists, created by the currently-logged-in staff user.
        # Create another library as staff:
        library2_key = self._create_library(library="lib2")
        # Login as ns_user:
        self._login_as_non_staff_user()

        # ns_user shouldn't be able to access any libraries:
        lib_list = self._list_libraries()
        self.assertEqual(len(lib_list), 0)
        self.assertFalse(self._can_access_library(self.library))
        self.assertFalse(self._can_access_library(library2_key))

        # Now manually intervene to give ns_user access to library2_key:
        access_role(library2_key).add_users(self.ns_user)

        # Now ns_user should be able to access library2_key only:
        lib_list = self._list_libraries()
        self.assertEqual(len(lib_list), 1)
        self.assertEqual(lib_list[0]["library_key"], unicode(library2_key))
        self.assertTrue(self._can_access_library(library2_key))
        self.assertFalse(self._can_access_library(self.library))

    @ddt.data(
        OrgStaffRole,
        OrgInstructorRole,
        OrgLibraryUserRole,
    )
    def test_org_based_access(self, org_access_role):
        """
        Test the various roles that allow viewing all of an organization's
        libraries are working correctly.
        """
        # Create some libraries as the staff user:
        lib_key_pacific = self._create_library(org="PacificX", library="libP")
        lib_key_atlantic = self._create_library(org="AtlanticX", library="libA")

        # Login as a non-staff:
        self._login_as_non_staff_user()

        # Now manually intervene to give ns_user access to all "PacificX" libraries:
        org_access_role(lib_key_pacific.org).add_users(self.ns_user)

        # Now ns_user should be able to access lib_key_pacific only:
        lib_list = self._list_libraries()
        self.assertEqual(len(lib_list), 1)
        self.assertEqual(lib_list[0]["library_key"], unicode(lib_key_pacific))
        self.assertTrue(self._can_access_library(lib_key_pacific))
        self.assertFalse(self._can_access_library(lib_key_atlantic))
        self.assertFalse(self._can_access_library(self.lib_key))

    @ddt.data(True, False)
    def test_read_only_role(self, use_org_level_role):
        """
        Test the read-only role (LibraryUserRole and its org-level equivalent)
        """
        # As staff user, add a block to self.library:
        block = ItemFactory.create(category="html", parent_location=self.library.location, user_id=self.user.id, publish_item=False)

        # Login as a ns_user:
        self._login_as_non_staff_user()
        self.assertFalse(self._can_access_library(self.library))

        block_url = reverse_usage_url('xblock_handler', block.location)

        def can_read_block():
            """ Check if studio lets us view the XBlock in the library """
            response = self.client.get_json(block_url)
            self.assertIn(response.status_code, (200, 403))  # 400 would be ambiguous
            return response.status_code == 200

        def can_edit_block():
            """ Check if studio lets us edit the XBlock in the library """
            response = self.client.ajax_post(block_url)
            self.assertIn(response.status_code, (200, 403))  # 400 would be ambiguous
            return response.status_code == 200

        def can_delete_block():
            """ Check if studio lets us delete the XBlock in the library """
            response = self.client.delete(block_url)
            self.assertIn(response.status_code, (200, 403))  # 400 would be ambiguous
            return response.status_code == 200

        def can_copy_block():
            """ Check if studio lets us duplicate the XBlock in the library """
            response = self.client.ajax_post(reverse_url('xblock_handler'), {
                'parent_locator': unicode(self.library.location),
                'duplicate_source_locator': unicode(block.location),
            })
            self.assertIn(response.status_code, (200, 403))  # 400 would be ambiguous
            return response.status_code == 200

        def can_create_block():
            """ Check if studio lets us make a new XBlock in the library """
            response = self.client.ajax_post(reverse_url('xblock_handler'), {
                'parent_locator': unicode(self.library.location), 'category': 'html',
            })
            self.assertIn(response.status_code, (200, 403))  # 400 would be ambiguous
            return response.status_code == 200

        # Check that we do not have read or write access to block:
        self.assertFalse(can_read_block())
        self.assertFalse(can_edit_block())
        self.assertFalse(can_delete_block())
        self.assertFalse(can_copy_block())
        self.assertFalse(can_create_block())

        # Give ns_user read-only permission:
        if use_org_level_role:
            OrgLibraryUserRole(self.lib_key.org).add_users(self.ns_user)
        else:
            LibraryUserRole(self.lib_key).add_users(self.ns_user)

        self.assertTrue(self._can_access_library(self.library))
        self.assertTrue(can_read_block())
        self.assertFalse(can_edit_block())
        self.assertFalse(can_delete_block())
        self.assertFalse(can_copy_block())
        self.assertFalse(can_create_block())
