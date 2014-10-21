"""
'library' XBlock/XModule

The "library" XBlock/XModule is the root of every content library structure
tree. All content blocks in the library are its children. It is analagous to
the "course" XBlock/XModule used as the root of each normal course structure
tree.

This block should only ever be present in the "library" branch of a course,
and it should never have a parent block.
"""
import logging

from xmodule.vertical_module import VerticalDescriptor, VerticalModule

from xblock.fields import Scope, String, List

log = logging.getLogger(__name__)

# Make '_' a no-op so we can scrape strings
_ = lambda text: text


class LibraryFields(object):
    """
    Fields of the "library" XBlock - see below.
    """
    display_name = String(
        help=_("Enter the name of the library as it should appear in Studio."),
        default="Library",
        display_name=_("Library Display Name"),
        scope=Scope.settings
    )
    advanced_modules = List(
        display_name=_("Advanced Module List"),
        help=_("Enter the names of the advanced components to use in your library."),
        scope=Scope.settings
    )
    has_children = True


class LibraryDescriptor(LibraryFields, VerticalDescriptor):
    """
    Descriptor for our library XBlock/XModule.
    """
    module_class = VerticalModule

    def __init__(self, *args, **kwargs):
        """
        Expects the same arguments as XModuleDescriptor.__init__
        """
        super(LibraryDescriptor, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u"Library: {}".format(self.display_name)

    def __str__(self):
        return "Library: {}".format(self.display_name)

    @property
    def display_org_with_default(self):
        """
        Return a display organization if it has been specified, otherwise return the 'org' that is in the location.
        """
        # TODO:
        #if self.display_organization:
        #    return self.display_organization
        return self.location.course_key.org

    @property
    def display_number_with_default(self):
        """
        Return a display course number if it has been specified, otherwise return the 'library' that is in the location
        """
        # TODO:
        #if self.display_coursenumber:
        #    return self.display_coursenumber
        return self.location.course_key.library
