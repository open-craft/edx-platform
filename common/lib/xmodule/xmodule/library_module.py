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

from xblock.fields import Scope, String, List, Boolean
from xblock.fragment import Fragment
from xmodule.library_content_module import XBlock

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
    show_children_previews = Boolean(
        display_name=_("Hide children preview"),
        help=_("Choose if preview of library contents is shown"),
        scope=Scope.user_state,
        default=True
    )
    has_children = True


class LibraryModule(LibraryFields, VerticalModule):
    def author_view(self, context):
        """
        Renders the Studio preview view.
        """
        fragment = Fragment()
        self.render_children(context, fragment, can_reorder=False, can_add=True)
        return fragment

    def render_children(self, context, fragment, can_reorder=False, can_add=False):  # pylint: disable=unused-argument
        """
        Renders the children of the module with HTML appropriate for Studio. If can_reorder is True,
        then the children will be rendered to support drag and drop.
        """
        contents = []

        paging = context.get('paging', None)

        children_count = len(self.children)
        item_start, item_end = 0, children_count

        # TODO sort children
        if paging:
            page_number = paging.get('page_number', 0)
            raw_page_size = paging.get('page_size', None)
            page_size = raw_page_size if raw_page_size is not None else children_count
            item_start, item_end = page_size*page_number, page_size*(page_number+1)

        children_to_show = self.children[item_start:item_end]

        for child_key in children_to_show:  # pylint: disable=E1101
            child = self.runtime.get_block(child_key)
            child_view_name = LibraryModule.get_preview_view_name(child)
            rendered_child = self.render_child(child, child_view_name, context)
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
                'can_reorder': False,
                'first_displayed': item_start,
                'total_children': children_count,
                'displayed_children': len(children_to_show),
                'previews': self.show_children_previews
            })
        )

    def render_child(self, child, child_view_name, context):
        child_context = context.copy()  # shallow copy should be enough
        if not self.show_children_previews:
            child_context['show_preview'] = False
        return self.runtime.render_child(child, child_view_name, child_context)
        # if self.show_children_previews:
        #     return self.runtime.render_child(child, child_view_name, context)
        # else:
        #     template_context = {
        #         'xblock_context': context,
        #         'xblock': child,
        #         'content': "",
        #         'is_root': False,
        #         'is_reorderable': False,
        #     }
        #     html = self.system.render_template('studio_xblock_wrapper.html', template_context)
        #     return Fragment(content=html)


@XBlock.wants('user')
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

    @XBlock.json_handler
    def trigger_previews(self, request_body, suffix):
        self.show_children_previews = request_body.get('show_children_previews', self.show_children_previews)
        user_id = self.runtime.service(self, 'user').user_id
        self.system.modulestore.update_item(self, user_id)
        return {'show_children_previews': self.show_children_previews}




