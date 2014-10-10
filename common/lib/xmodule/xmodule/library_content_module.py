from collections import namedtuple
from copy import copy
import json
from opaque_keys.edx.locator import CourseLocator
from xblock.fields import Scope, String, List, Integer, Boolean
from xblock.fragment import Fragment
from xmodule.x_module import XModule, STUDENT_VIEW
from xmodule.seq_module import SequenceDescriptor
from xmodule.studio_editable import StudioEditableModule, StudioEditableDescriptor
from pkg_resources import resource_string

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

class LibraryVersionReference(namedtuple("LibraryVersionReference", "library_id version")):
    """
    A reference to a specific library, with an optional version.
    The version is used to find out when the LibraryContentXBlock was last
    updated with the latest content from the library.
    """
    def __new__(cls, library_id, version=None):
        # pylint: disable=super-on-old-class
        if not isinstance(library_id, CourseLocator):
            library_id = CourseLocator.from_string(library_id)
        if library_id.version:
            assert (version is None) or (version == library_id.version)
            if not version:
                version = library_id.version
            library_id = library_id.for_version(None)
        return super(LibraryVersionReference, cls).__new__(cls, library_id, version)

    @staticmethod
    def from_json(value):
        return LibraryVersionReference(*value)

    def to_json(self):
        # TODO: Is there anyway for an xblock to store an ObjectId as
        # part of the List() field value? self.version should really be
        # stored in mongo as an ObjectId.
        return [unicode(self.library_id), self.version if self.version else None]

class LibraryList(List):
    """
    Special List class for listing references to content libraries.
    Is simply a list of LibraryVersionReference tuples.
    """
    def from_json(self, values):
        # values might be a list of lists, or a list of strings
        # Normally the runtime gives us:
        # [[u'course-v1:ProblemX+PR0B+2014+branch@library', '5436ffec56c02c13806a4c1b'], ...]
        # But the studio editor gives us:
        # [u'course-v1:ProblemX+PR0B+2014+branch@library,5436ffec56c02c13806a4c1b', ...]
        # TODO: Fix studio's strange behaviour or get a custom widget
        def parse(val):
            if isinstance(val, unicode) or isinstance(val, str):
                val = val.strip(' []')
                parts = val.rsplit(',', 1)
                val = [parts[0], parts[1] if len(parts) > 1 else None]
            return LibraryVersionReference.from_json(val)
        return [parse(v) for v in values]

    def to_json(self, values):
        return [lvr.to_json() for lvr in values]


class LibraryContentFields(object):
    source_libraries = LibraryList(
        display_name=_("Library"),
        help=_("Which content library to draw content from"),
        default=[],
        scope=Scope.settings,
    )
    mode = String(
        help=_("Determines how content is drawn from the library"),
        default="random",
        values=[
            {"display_name": _("Choose first n"), "value": "first"},
            {"display_name": _("Choose n at random"), "value": "random"}
            #{"display_name": _("Manually selected"), "value": "manual"}
        ],
        scope=Scope.settings,
    )
    max_count = Integer(
        display_name=_("Count"),
        help=_("How many components to select from the library"),
        default=1,
        scope=Scope.settings,
    )
    filters = String(default="")  # TBD
    has_score = Boolean(
        display_name=_("Graded"),
        help=_("Is this a graded assignment"),
        default=False,
        scope=Scope.settings,
    )
    weight = Integer(
        display_name=_("Weight"),
        help=_("If this is a graded assignment, this determines the total point value available."),
        default=1,
        scope=Scope.settings,
    )
    has_children = True


class LibraryContentModule(LibraryContentFields, XModule, StudioEditableModule):
    ''' Layout module for laying out submodules vertically.'''

    def student_view(self, context):
        fragment = Fragment()
        contents = []

        child_context = {} if not context else copy(context)
        child_context['child_of_vertical'] = True

        for child in self.get_display_items():
            rendered_child = child.render(STUDENT_VIEW, child_context)
            fragment.add_frag_resources(rendered_child)

            contents.append({
                'id': child.location.to_deprecated_string(),
                'content': rendered_child.content
            })

        fragment.add_content(self.system.render_template('vert_module.html', {
            'items': contents,
            'xblock_context': context,
        }))
        return fragment

    def author_view(self, context):
        """
        Renders the Studio views.
        Normal studio view: displays library status and has an "Update" button.
        Studio container view: displays a preview of all possible children.
        """
        fragment = Fragment()
        root_xblock = context.get('root_xblock')
        is_root = root_xblock and root_xblock.location == self.location

        # When used on a unit page, don't show any sort of preview - just the status of this block.
        # For the container page we show a preview of all possible children
        if is_root or not context.get('is_unit_page'):
            self.render_children(context, fragment, can_reorder=False, can_add=False)
        return fragment


class LibraryContentDescriptor(LibraryContentFields, SequenceDescriptor, StudioEditableDescriptor):
    """
    Descriptor class for LibraryContentModule XBlock.
    """
    module_class = LibraryContentModule

    js = {'coffee': [resource_string(__name__, 'js/src/vertical/edit.coffee')]}
    js_module_name = "VerticalDescriptor"

    # TODO: definition_to_xml etc.

    @property
    def non_editable_metadata_fields(self):
        # Don't show a "due date" field in the editor for this block
        non_editable_fields = super(LibraryContentDescriptor, self).non_editable_metadata_fields
        non_editable_fields.extend([
            LibraryContentDescriptor.due,
        ])
        return non_editable_fields
