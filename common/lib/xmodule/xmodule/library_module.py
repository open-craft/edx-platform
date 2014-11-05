"""
'library' XBlock/XModule

The "library" XBlock/XModule is the root of every content library structure
tree. All content blocks in the library are its children. It is analagous to
the "course" XBlock/XModule used as the root of each normal course structure
tree.
"""
import math
import logging

from xmodule.vertical_module import VerticalDescriptor, VerticalModule

from xblock.fields import Scope, String, List
from xblock.fragment import Fragment

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


class LibraryModule(LibraryFields, VerticalModule):
    def author_view(self, context):
        """
        Renders the Studio preview view.
        """
        fragment = Fragment()
        root_xblock = context.get('root_xblock')
        is_root = root_xblock and root_xblock.location == self.location

        # For the container page we want the full drag-and-drop, but for unit pages we want
        # a more concise version that appears alongside the "View =>" link-- unless it is
        # the unit page and the vertical being rendered is itself the unit vertical (is_root == True).
        if is_root or not context.get('is_unit_page'):
            self.render_children(context, fragment, can_reorder=False, can_add=True)
        return fragment

    def render_children(self, context, fragment, can_reorder=False, can_add=False):
        """
        Renders the children of the module with HTML appropriate for Studio. If can_reorder is True,
        then the children will be rendered to support drag and drop.
        """
        contents = []

        children = self.descriptor.get_children()
        paging = context.get('paging', None)
        children_count = len(children)

        item_start = 0
        children_to_show = children

        # TODO modify paging so that only requested children are fetched
        if paging:
            page_number = paging.get('page_number', 0)
            raw_page_size = paging.get('page_size', None)
            page_size = raw_page_size if raw_page_size is not None else children_count
            item_start, item_end = page_size*page_number, page_size*(page_number+1)
            children_to_show = children[item_start:item_end]

        for child in children_to_show:  # pylint: disable=E1101
            if can_reorder:
                context['reorderable_items'].add(child.location)
            child_module = self.system.get_module(child)  # pylint: disable=E1101
            rendered_child = child_module.render(LibraryModule.get_preview_view_name(child_module), context)
            fragment.add_frag_resources(rendered_child)

            contents.append({
                'id': child.location.to_deprecated_string(),
                'content': rendered_child.content
            })

        fragment.add_content(
            self.system.render_template("studio_render_paged_children_view.html", {  # pylint: disable=E1101
                'items': contents,
                'xblock_context': context,
                'can_add': can_add,
                'can_reorder': can_reorder,
                'first_displayed': item_start,
                'total_children': children_count,
                'displayed_children': len(children_to_show)
            }
        ))


class LibraryDescriptor(LibraryFields, VerticalDescriptor):
    """
    Descriptor for our library XBlock/XModule.
    """
    module_class = LibraryModule

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
        return self.location.course_key.org

    @property
    def display_number_with_default(self):
        """
        Return a display course number if it has been specified, otherwise return the 'library' that is in the location
        """
        return self.location.course_key.library

    @classmethod
    def from_xml(cls, xml_data, system, id_generator):
        """ XML support not yet implemented. """
        raise NotImplementedError

    def export_to_xml(self, resource_fs):
        """ XML support not yet implemented. """
        raise NotImplementedError
