"""
XBlock runtime services for LibraryContentModule
"""
from opaque_keys.edx.locator import LibraryLocator
from xmodule.library_content_module import LibraryVersionReference
from xmodule.modulestore.exceptions import ItemNotFoundError


class LibraryToolsService(object):
    """
    Service that allows LibraryContentModule to interact with libraries in the
    modulestore.
    """
    def __init__(self, modulestore):
        self.store = modulestore

    def _get_library(self, library_key):
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
        library = self._get_library(lib_key)
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
        library = self._get_library(lib_key)
        if library:
            return library.display_name
        return None

    def update_children(self, dest_block, user_id):
        """
        This method is to be used when any of the libraries that a LibraryContentModule
        references have been updated. It will re-fetch all matching blocks from
        the libraries, and copy them as children of dest_block. The children
        will be given new block_ids, but the definition ID used should be the
        exact same definition ID used in the library.

        This method will update dest_block's 'source_libraries' field to store
        the version number of the libraries used, so we easily determine if
        dest_block is up to date or not.
        """
        new_libraries = []
        source_blocks = []
        for library_key, dummy in dest_block.source_libraries:
            library = self._get_library(library_key)
            if library is None:
                raise ValueError("Required library not found.")
            source_blocks.extend(library.children)  # In future, this will be filtered so only specific children are used.
            new_libraries.append(LibraryVersionReference(library_key, library.location.library_key.version_guid))

        with self.store.bulk_operations(dest_block.location.course_key):
            dest_block.source_libraries = new_libraries
            self.store.update_item(dest_block, user_id)
            dest_block.children = self.store.inherit_copy(source_blocks, dest_block.location, user_id, copy_children=True)
            # ^-- inherit_copy updates the children in the DB but we must also set .children here to avoid overwriting the DB again
