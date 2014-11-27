"""
Fixture to create a Content Library
"""

from .course import StudioApiFixture
import json
from opaque_keys.edx.keys import CourseKey

from . import STUDIO_BASE_URL


class LibraryFixtureError(Exception):
    """
    Error occurred while installing a library fixture.
    """
    pass


class LibraryFixture(StudioApiFixture):
    """
    Fixture for ensuring that a library exists.

    WARNING: This fixture is NOT idempotent.  To avoid conflicts
    between tests, you should use unique library identifiers for each fixture.
    """

    def __init__(self, org, number, display_name):
        """
        Configure the library fixture to create a library with
        """
        super(LibraryFixture, self).__init__()
        self.library_info = {
            'org': org,
            'number': number,
            'display_name': display_name
        }

        self.children = []
        self._library_key = None

    def __str__(self):
        """
        String representation of the library fixture, useful for debugging.
        """
        return "<LibraryFixture: org='{org}', number='{number}'>".format(**self.library_info)

    def add_children(self, *args):
        """
        Add children XBlock to the library.
        Each item in `args` is an `XBlockFixtureDesc` object.

        Returns the library fixture to allow chaining.
        """
        self.children.extend(args)
        return self

    def install(self):
        """
        Create the library and XBlocks within the library.
        This is NOT an idempotent method; if the library already exists, this will
        raise a `LibraryFixtureError`.  You should use unique library identifiers to avoid
        conflicts between tests.
        """
        self._create_library()
        self._create_xblock_children(self.library_location, self.children)

        return self

    @property
    def library_key(self):
        """
        Get the LibraryLocator for this library, as a string.
        """
        return self._library_key

    @property
    def library_location(self):
        """
        Return the locator string for the LibraryRoot XBlock that is the root of the library hierarchy.
        """
        lib_key = CourseKey.from_string(self._library_key)
        return unicode(lib_key.make_usage_key('library', 'library'))

    def _create_library(self):
        """
        Create the library described in the fixture.
        Will fail if the library already exists.
        """
        response = self.session.post(
            STUDIO_BASE_URL + '/library/',
            data=self._encode_post_dict(self.library_info),
            headers=self.headers
        )

        if response.ok:
            self._library_key = response.json()['library_key']
        else:
            try:
                err_msg = response.json().get('ErrMsg')
            except ValueError:
                err_msg = "Unknown Error"
            raise LibraryFixtureError(
                "Could not create library {}. Status was {}, error was: {}".format(self.library_info, response.status_code, err_msg)
            )

    def _create_xblock_children(self, parent_loc, xblock_descriptions):
        """
        Recursively create XBlock children.
        """
        for desc in xblock_descriptions:
            loc = self.create_xblock(parent_loc, desc)
            self._create_xblock_children(loc, desc.children)

    def create_xblock(self, parent_loc, xblock_desc):
        """
        Create an XBlock with `parent_loc` (the location of the parent block)
        and `xblock_desc` (an `XBlockFixtureDesc` instance).
        """
        # Disable publishing for library XBlocks:
        xblock_desc.publish = "not-applicable"

        create_payload = {
            'category': xblock_desc.category,
            'display_name': xblock_desc.display_name,
        }

        if parent_loc is not None:
            create_payload['parent_locator'] = parent_loc

        # Create the new XBlock
        response = self.session.post(
            STUDIO_BASE_URL + '/xblock/',
            data=json.dumps(create_payload),
            headers=self.headers,
        )

        if not response.ok:
            msg = "Could not create {0}.  Status was {1}".format(xblock_desc, response.status_code)
            raise LibraryFixtureError(msg)

        try:
            loc = response.json().get('locator')
            xblock_desc.locator = loc
        except ValueError:
            raise LibraryFixtureError("Could not decode JSON from '{0}'".format(response.content))

        # Configure the XBlock
        response = self.session.post(
            STUDIO_BASE_URL + '/xblock/' + loc,
            data=xblock_desc.serialize(),
            headers=self.headers,
        )

        if response.ok:
            return loc
        else:
            raise LibraryFixtureError("Could not update {0}.  Status code: {1}".format(xblock_desc, response.status_code))

    def _update_xblock(self, locator, data):
        """
        Update the xblock at `locator`.
        """
        # Create the new XBlock
        response = self.session.put(
            "{}/xblock/{}".format(STUDIO_BASE_URL, locator),
            data=json.dumps(data),
            headers=self.headers,
        )

        if not response.ok:
            msg = "Could not update {} with data {}.  Status was {}".format(locator, data, response.status_code)
            raise LibraryFixtureError(msg)

    def _encode_post_dict(self, post_dict):
        """
        Encode `post_dict` (a dictionary) as UTF-8 encoded JSON.
        """
        return json.dumps({
            k: v.encode('utf-8') if isinstance(v, basestring) else v
            for k, v in post_dict.items()
        })
