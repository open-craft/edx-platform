from bson.objectid import ObjectId
from collections import namedtuple
from copy import copy
import hashlib
from .mako_module import MakoModuleDescriptor
from opaque_keys.edx.locator import CourseLocator
import random
from webob import Response
from xblock.core import XBlock
from xblock.fields import Scope, String, List, Integer, Boolean
from xblock.fragment import Fragment
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.x_module import XModule, STUDENT_VIEW
from xmodule.studio_editable import StudioEditableModule, StudioEditableDescriptor
from .xml_module import XmlDescriptor
from pkg_resources import resource_string

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

# enum helper in lieu of enum34
def enum(**enums):
    return type('Enum', (), enums)

class LibraryVersionReference(namedtuple("LibraryVersionReference", "library_id version")):
    """
    A reference to a specific library, with an optional version.
    The version is used to find out when the LibraryContentXBlock was last
    updated with the latest content from the library.

    library_id is a CourseLocator
    version is an ObjectId or None
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
        if version and not isinstance(version, ObjectId):
            version = ObjectId(version)
        return super(LibraryVersionReference, cls).__new__(cls, library_id, version)

    @staticmethod
    def from_json(value):
        return LibraryVersionReference(*value)

    def to_json(self):
        # TODO: Is there anyway for an xblock to *store* an ObjectId as
        # part of the List() field value? self.version should really be
        # stored in mongo as an ObjectId.
        return [unicode(self.library_id), unicode(self.version) if self.version else None]

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
        display_name=_("Scored"),
        help=_("Set this true if this is meant to be either a graded assignment or a practice problem."),
        default=False,
        scope=Scope.settings,
    )
    weight = Integer(
        display_name=_("Weight"),
        help=_("If this is scored, the total possible score will be scaled to this weight."),
        default=1,
        scope=Scope.settings,
    )
    selected = List(
        # This is a list of block_ids used to record which random/first set of matching blocks was selected per user
        default=[],
        scope=Scope.user_state,
    )
    has_children = True


class LibraryContentModule(LibraryContentFields, XModule, StudioEditableModule):
    """
    An XBlock whose children are chosen dynamically from a content library.
    Can be used to create randomized assessments among other things.

    Note: technically, all matching blocks from the content library are added
    as children of this block, but only a subset of those children are shown to
    any particular student.
    """

    def student_view(self, context):
        # Determine which of our children we will show:
        selected = set(self.selected) if self.selected else set()  # set of block_ids
        valid_block_ids = set([c.block_id for c in self.children])
        # Remove any selected blocks that are no longer valid:
        selected -= (selected - valid_block_ids)
        # If max_count has been decreased, we may have to drop some previously selected blocks:
        while len(selected) > self.max_count:
            selected.pop()
        # Do we have enough blocks now?
        num_to_add = self.max_count - len(selected)
        if num_to_add > 0:
            # We need to select [more] blocks to display to this user:
            if self.mode == "random":
                pool = valid_block_ids - selected
                num_to_add = min(len(pool), num_to_add)
                selected |= set(random.sample(pool, num_to_add))
                # We now have the correct n random children to show for this user.
            elif self.mode == "first":
                for c in self.children:
                    if c.block_id not in selected:
                        selected += c.block_id
                        if len(selected) == self.max_count:
                            break
            else:
                raise NotImplementedError("Unsupported mode.")
        # Save our selections to the user state, to ensure consistency:
        self.selected = list(selected)

        fragment = Fragment()
        contents = []
        child_context = {} if not context else copy(context)

        for child_loc in self.children:
            if child_loc.block_id not in selected:
                continue
            child = self.runtime.get_block(child_loc)
            for displayable in child.displayable_items():
                rendered_child = displayable.render(STUDENT_VIEW, child_context)
                fragment.add_frag_resources(rendered_child)
                contents.append({
                    'id': displayable.location.to_deprecated_string(),
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

        if is_root:
            # User has clicked the "View" link. Show a preview of all possible children:
            if self.children:
                self.render_children(context, fragment, can_reorder=False, can_add=False)
            else:
                fragment.add_content(u'<p>{}</p>'.format(
                    _('No matching content found in library, no library configured, or not yet loaded from library.')
                ))
        else:
            # When shown on a unit page, don't show any sort of preview - just the status of this block.
            LibraryStatus = enum(
                NONE=0,  # no library configured
                INVALID=1,  # invalid configuration or library has been deleted/corrupted
                OK=2,  # library configured correctly and should be working fine
            )
            UpdateStatus = enum(
                CANNOT=0,  # Cannot update - library is not set, invalid, deleted, etc.
                NEEDED=1,  # An update is needed - prompt the user to update
                UP_TO_DATE=2,  # No update necessary - library is up to date
            )
            library_names = []
            library_status = LibraryStatus.OK
            update_status = UpdateStatus.UP_TO_DATE
            if self.source_libraries:
                for library_key, version in self.source_libraries:
                    library = self._get_library(library_key)
                    if library is None:
                        library_status = LibraryStatus.INVALID
                        update_status = UpdateStatus.CANNOT
                        break
                    library_names.append(library.display_name)
                    latest_version = library.location.course_key.version
                    if version is None or version != latest_version:
                        update_status=UpdateStatus.NEEDED
                    # else library is up to date. 
            else:
                library_status = LibraryStatus.NONE
                update_status = UpdateStatus.CANNOT
            fragment.add_content(self.system.render_template('library-block-author-view.html', {
                'library_status': library_status,
                'LibraryStatus': LibraryStatus,
                'update_status': update_status,
                'UpdateStatus': UpdateStatus,
                'library_names': library_names,
                'max_count': self.max_count,
                'mode': self.mode,
                'num_children': len(self.children),
            }))
            fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/library_content_edit.js'))
            fragment.initialize_js('LibraryContentAuthorView')
        return fragment

    def _get_library(self, library_key):
        """
        Given a library key like "course-v1:ProblemX+PR0B+2014+branch@library",
        return the 'library' XBlock with meta-information about the library.

        Returns None on error.
        """
        if not isinstance(library_key, CourseLocator):
            library_key = CourseLocator.from_string(library_key)
        assert library_key.version is None

        # TODO: Is this too tightly coupled to split? May need to abstract this into a service
        # provided by the CMS runtime.
        try:
            library = self.runtime.descriptor_runtime.modulestore.get_course(library_key, remove_branch=False, remove_version=False)
        except ItemNotFoundError:
            return None
        # library's version should be in library.location.course_key.version
        # TODO: Is this guaranteed?
        assert library.location.course_key.version is not None
        # Note library version is also possibly available at library.runtime.course_entry.course_key.version
        return library


@XBlock.wants('user')
class LibraryContentDescriptor(LibraryContentFields, MakoModuleDescriptor, XmlDescriptor, StudioEditableDescriptor):
    """
    Descriptor class for LibraryContentModule XBlock.
    """
    mako_template = 'widgets/metadata-edit.html'
    module_class = LibraryContentModule

    @XBlock.handler
    def refresh_children(self, request, _):
        """
        Refresh children:
        This method is to be used when any of the libraries that this block
        references have been updated. It will re-fetch all matching blocks from
        the libraries, and copy them as children of this block. The children
        will be given new block_ids, but the definition ID used should be the
        exact same definition ID used in the library.

        This method will update this block's 'source_libraries' field to store
        the version number of the libraries used, so we easily determine if
        this block is up to date or not.
        """
        user_id = self.runtime.service(self, 'user').user_id
        new_children = []

        store = self.system.modulestore
        with store.bulk_operations(self.location.course_key):
            # First, delete all our existing children:
            for c in self.children:
                store.delete_item(c, user_id)
            # Now add all matching children, and record the library version we use:
            new_libraries = []
            for library_key, version in self.source_libraries:
                library = self._xmodule._get_library(library_key)
                for c in library.children:
                    child = store.get_item(c, depth=9)
                    # We compute a block_id for each matching child block found in the library.
                    # block_ids are unique within any branch, but are not unique per-course or globally.
                    # We need our block_ids to be consistent when content in the library is updated, so
                    # we compute block_id as a hash of three pieces of data:
                    unique_data = "{}:{}:{}".format(
                        self.location.block_id,  # Must not clash with other usages of the same library in this course
                        unicode(library_key.for_version(None)).encode("utf-8"),  # The block ID below is only unique within a library, so we need this too
                        c.block_id,  # Child block ID. Should not change even if the block is edited.
                    )
                    child_block_id = hashlib.sha1(unique_data).hexdigest()[:20]
                    new_child_info = store.create_item(
                        user_id,
                        self.location.course_key,
                        c.block_type,
                        block_id=child_block_id,
                        definition_locator=child.definition_locator,
                        # TODO: metadata= (data from Scope.settings fields) - as temporary thing until they get stored in definitions,
                        runtime=self.system,
                    )
                    new_children.append(new_child_info.location)
                new_libraries.append(LibraryVersionReference(library_key, library.location.course_key.version))
            self.source_libraries = new_libraries
            self.children = new_children
            self.system.modulestore.update_item(self, None)
        return Response()

    def has_dynamic_children(self):
        """
        Inform the runtime that our children vary per-user.
        """
        return True

    js = {'coffee': [resource_string(__name__, 'js/src/vertical/edit.coffee')]}
    js_module_name = "VerticalDescriptor"

    # TODO: definition_to_xml etc.
