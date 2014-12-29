"""
XBlock runtime services for LibraryContentModule
"""
import hashlib
from opaque_keys.edx.locator import LibraryLocator
from xblock.fields import Scope
from xmodule.library_content_module import LibraryVersionReference, ANY_CAPA_TYPE_VALUE
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.capa_module import CapaDescriptor


class LibraryToolsService(object):
    """
    Service that allows LibraryContentModule to interact with libraries in the
    modulestore.
    """
    def __init__(self, modulestore):
        self.store = modulestore

    def get_library(self, library_key):
        """
        Given a library key like "library-v1:ProblemX+PR0B", return the
        'library' XBlock with meta-information about the library.

        Returns None on error.
        """
        if not isinstance(library_key, LibraryLocator):
            library_key = LibraryLocator.from_string(library_key)
        assert library_key.version_guid is None

        try:
            return self.store.get_library(library_key, remove_version=False)
        except ItemNotFoundError:
            return None

    def get_library_version(self, lib_key):
        """
        Get the version (an ObjectID) of the given library.
        Returns None if the library does not exist.
        """
        library = self.get_library(lib_key)
        if library:
            # We need to know the library's version so ensure it's set in library.location.library_key.version_guid
            assert library.location.library_key.version_guid is not None
            return library.location.library_key.version_guid
        return None

    def get_library_display_name(self, lib_key):
        """
        Get the display_name of the given library.
        Returns None if the library does not exist.
        """
        library = self.get_library(lib_key)
        if library:
            return library.display_name
        return None

    def _filter_child(self, capa_type, child_descriptor):
        """
        Filters children by CAPA problem type, if configured
        """
        if capa_type == ANY_CAPA_TYPE_VALUE:
            return True

        if not isinstance(child_descriptor, CapaDescriptor):
            return False

        return capa_type in child_descriptor.problem_types

    def get_filtered_children(self, from_block, capa_type=ANY_CAPA_TYPE_VALUE):
        """
        Filters children of `from_block` that satisfy filter criteria
        Returns generator containing (child_key, child) for all children matching filter criteria
        """
        children = (
            (child_key, self.store.get_item(child_key, depth=9))
            for child_key in from_block.children
        )
        return (
            (child_key, child)
            for child_key, child in children
            if self._filter_child(capa_type, child)
        )

    def update_children(self, dest_block, user_id, update_db=True):
        """
        This method is to be used when any of the libraries that a LibraryContentModule
        references have been updated. It will re-fetch all matching blocks from
        the libraries, and copy them as children of dest_block. The children
        will be given new block_ids, but the definition ID used should be the
        exact same definition ID used in the library.

        This method will update dest_block's 'source_libraries' field to store
        the version number of the libraries used, so we easily determine if
        dest_block is up to date or not.

        If update_db is True (default), this will explicitly persist the changes
        to the modulestore by calling update_item(). Only set update_db False if
        you know for sure that dest_block is about to be saved to the modulestore
        anyways. Otherwise, orphaned blocks may be created.
        """
        root_children = []

        with self.store.bulk_operations(dest_block.location.course_key):
            # Currently, ALL children are essentially deleted and then re-added
            # in a way that preserves their block_ids (and thus should preserve
            # student data, grades, analytics, etc.)
            # Once course-level field overrides are implemented, this will
            # change to a more conservative implementation.

            # First, load and validate the source_libraries:
            libraries = []
            for library_key, old_version in dest_block.source_libraries:  # pylint: disable=unused-variable
                library = self.get_library(library_key)
                if library is None:
                    raise ValueError("Required library not found.")
                libraries.append((library_key, library))

            # Next, delete all our existing children to avoid block_id conflicts when we add them:
            for child in dest_block.children:
                self.store.delete_item(child, user_id)

            # Now add all matching children, and record the library version we use:
            new_libraries = []
            for library_key, library in libraries:

                def copy_children_recursively(from_block, filter_problem_type=False):
                    """
                    Internal method to copy blocks from the library recursively
                    """
                    new_children = []
                    target_capa_type = dest_block.capa_type if filter_problem_type else ANY_CAPA_TYPE_VALUE
                    filtered_children = self.get_filtered_children(from_block, target_capa_type)
                    for child_key, child in filtered_children:
                        # We compute a block_id for each matching child block found in the library.
                        # block_ids are unique within any branch, but are not unique per-course or globally.
                        # We need our block_ids to be consistent when content in the library is updated, so
                        # we compute block_id as a hash of three pieces of data:
                        unique_data = "{}:{}:{}".format(
                            dest_block.location.block_id,  # Must not clash with other usages of the same library in this course
                            unicode(library_key.for_version(None)).encode("utf-8"),  # The block ID below is only unique within a library, so we need this too
                            child_key.block_id,  # Child block ID. Should not change even if the block is edited.
                        )
                        child_block_id = hashlib.sha1(unique_data).hexdigest()[:20]
                        fields = {}
                        for field in child.fields.itervalues():
                            if field.scope == Scope.settings and field.is_set_on(child):
                                fields[field.name] = field.read_from(child)
                        if child.has_children:
                            fields['children'] = copy_children_recursively(from_block=child)
                        new_child_info = self.store.create_item(
                            user_id,
                            dest_block.location.course_key,
                            child_key.block_type,
                            block_id=child_block_id,
                            definition_locator=child.definition_locator,
                            runtime=dest_block.system,
                            fields=fields,
                        )
                        new_children.append(new_child_info.location)
                    return new_children
                root_children.extend(copy_children_recursively(from_block=library, filter_problem_type=True))
                new_libraries.append(LibraryVersionReference(library_key, library.location.library_key.version_guid))
            dest_block.source_libraries = new_libraries
            dest_block.children = root_children
            if update_db:
                self.store.update_item(dest_block, user_id)
