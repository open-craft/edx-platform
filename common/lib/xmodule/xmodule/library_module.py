import logging

from xmodule.vertical_module import VerticalDescriptor, VerticalModule

from xblock.fields import Scope, String

log = logging.getLogger(__name__)

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

class LibraryFields(object):
    display_name = String(
        help=_("Enter the name of the library as it should appear in Studio."),
        default="Library",
        display_name=_("Library Display Name"),
        scope=Scope.settings
    )
    has_children = True

class LibraryDescriptor(LibraryFields, VerticalDescriptor):
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
