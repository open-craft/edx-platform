"""
LibraryContent: The XBlock used to include blocks from a library in a course.
"""
from bson.objectid import ObjectId
from collections import namedtuple
from copy import copy
import hashlib
from .mako_module import MakoModuleDescriptor
from opaque_keys.edx.locator import LibraryLocator
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


def enum(**enums):
    """ enum helper in lieu of enum34 """
    return type('Enum', (), enums)


class LibraryVersionReference(namedtuple("LibraryVersionReference", "library_id version")):
    """
    A reference to a specific library, with an optional version.
    The version is used to find out when the LibraryContentXBlock was last
    updated with the latest content from the library.

    library_id is a LibraryLocator
    version is an ObjectId or None
    """
    def __new__(cls, library_id, version=None):
        # pylint: disable=super-on-old-class
        if not isinstance(library_id, LibraryLocator):
            library_id = LibraryLocator.from_string(library_id)
        if library_id.version_guid:
            assert (version is None) or (version == library_id.version_guid)
            if not version:
                version = library_id.version_guid
            library_id = library_id.for_version(None)
        if version and not isinstance(version, ObjectId):
            version = ObjectId(version)
        return super(LibraryVersionReference, cls).__new__(cls, library_id, version)

    @staticmethod
    def from_json(value):
        """
        Implement from_json to convert from JSON
        """
        return LibraryVersionReference(*value)

    def to_json(self):
        """
        Implement to_json to convert value to JSON
        """
        # TODO: Is there anyway for an xblock to *store* an ObjectId as
        # part of the List() field value?
        return [unicode(self.library_id), unicode(self.version) if self.version else None]  # pylint: disable=no-member


class LibraryList(List):
    """
    Special List class for listing references to content libraries.
    Is simply a list of LibraryVersionReference tuples.
    """
    def from_json(self, values):
        """
        Implement from_json to convert from JSON.

        values might be a list of lists, or a list of strings
        Normally the runtime gives us:
            [[u'library-v1:ProblemX+PR0B', '5436ffec56c02c13806a4c1b'], ...]
        But the studio editor gives us:
            [u'library-v1:ProblemX+PR0B,5436ffec56c02c13806a4c1b', ...]
        """
        def parse(val):
            """ Convert this list entry from its JSON representation """
            if isinstance(val, unicode) or isinstance(val, str):
                val = val.strip(' []')
                parts = val.rsplit(',', 1)
                val = [parts[0], parts[1] if len(parts) > 1 else None]
            return LibraryVersionReference.from_json(val)
        return [parse(v) for v in values]

    def to_json(self, values):
        """
        Implement to_json to convert value to JSON
        """
        return [lvr.to_json() for lvr in values]


class LibraryContentFields(object):
    """
    Fields for the LibraryContentModule.

    Separated out for now because they need to be added to the module and the
    descriptor.
    """
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
            {"display_name": _("Choose n at random"), "value": "random"}
            # Future addition: Choose a new random set of n every time the student refreshes the block, for self tests
            # Future addition: manually selected blocks
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
    selected = List(
        # This is a list of block_ids used to record which random/first set of matching blocks was selected per user
        default=[],
        scope=Scope.user_state,
    )
    has_children = True


def _get_library(modulestore, library_key):
    """
    Given a library key like "library-v1:ProblemX+PR0B", return the
    'library' XBlock with meta-information about the library.

    Returns None on error.
    """
    if not isinstance(library_key, LibraryLocator):
        library_key = LibraryLocator.from_string(library_key)
    assert library_key.version_guid is None

    # TODO: Is this too tightly coupled to split? May need to abstract this into a service
    # provided by the CMS runtime.
    try:
        library = modulestore.get_library(library_key, remove_version=False)
    except ItemNotFoundError:
        return None
    # We need to know the library's version so ensure it's set in library.location.library_key.version_guid
    assert library.location.library_key.version_guid is not None
    return library


#pylint: disable=abstract-method
class LibraryContentModule(LibraryContentFields, XModule, StudioEditableModule):
    """
    An XBlock whose children are chosen dynamically from a content library.
    Can be used to create randomized assessments among other things.

    Note: technically, all matching blocks from the content library are added
    as children of this block, but only a subset of those children are shown to
    any particular student.
    """
    def selected_children(self):
        """
        Returns a set() of block_ids indicating which of the possible children
        have been selected to display to the current user.

        This reads and updates the "selected" field, which has user_state scope.

        Note: self.selected and the return value contain block_ids. To get
        actual BlockUsageLocators, it is necessary to use self.children,
        because the block_ids alone do not specify the block type.
        """
        if hasattr(self, "_selected_set"):
            # Already done:
            return self._selected_set  # pylint: disable=access-member-before-definition
        # Determine which of our children we will show:
        selected = set(self.selected) if self.selected else set()  # set of block_ids
        valid_block_ids = set([c.block_id for c in self.children])  # pylint: disable=no-member
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
            else:
                raise NotImplementedError("Unsupported mode.")
        # Save our selections to the user state, to ensure consistency:
        self.selected = list(selected)  # TODO: this doesn't save from the LMS "Progress" page.
        # Cache the results
        self._selected_set = selected  # pylint: disable=attribute-defined-outside-init
        return selected

    def _get_selected_child_blocks(self):
        """
        Generator returning XBlock instances of the children selected for the
        current user.
        """
        selected = self.selected_children()
        for child_loc in self.children:  # pylint: disable=no-member
            if child_loc.block_id in selected:
                yield self.runtime.get_block(child_loc)

    def student_view(self, context):
        fragment = Fragment()
        contents = []
        child_context = {} if not context else copy(context)

        for child in self._get_selected_child_blocks():
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
            if self.children:  # pylint: disable=no-member
                self.render_children(context, fragment, can_reorder=False, can_add=False)
            else:
                fragment.add_content(u'<p>{}</p>'.format(
                    _('No matching content found in library, no library configured, or not yet loaded from library.')
                ))
        else:
            # When shown on a unit page, don't show any sort of preview - just the status of this block.
            LibraryStatus = enum(  # pylint: disable=invalid-name
                NONE=0,  # no library configured
                INVALID=1,  # invalid configuration or library has been deleted/corrupted
                OK=2,  # library configured correctly and should be working fine
            )
            UpdateStatus = enum(  # pylint: disable=invalid-name
                CANNOT=0,  # Cannot update - library is not set, invalid, deleted, etc.
                NEEDED=1,  # An update is needed - prompt the user to update
                UP_TO_DATE=2,  # No update necessary - library is up to date
            )
            library_names = []
            library_status = LibraryStatus.OK
            update_status = UpdateStatus.UP_TO_DATE
            if self.source_libraries:
                for library_key, version in self.source_libraries:
                    library = _get_library(self.runtime.descriptor_runtime.modulestore, library_key)
                    if library is None:
                        library_status = LibraryStatus.INVALID
                        update_status = UpdateStatus.CANNOT
                        break
                    library_names.append(library.display_name)
                    latest_version = library.location.library_key.version_guid
                    if version is None or version != latest_version:
                        update_status = UpdateStatus.NEEDED
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
                'num_children': len(self.children),  # pylint: disable=no-member
            }))
            fragment.add_javascript_url(self.runtime.local_resource_url(self, 'public/js/library_content_edit.js'))
            fragment.initialize_js('LibraryContentAuthorView')
        return fragment

    def get_child_descriptors(self):
        """
        We override normal handling of children.
        In this case, our goal is to prevent the LMS from expecting any grades
        from child XBlocks. So we tell the system that we have no children.
        This way, we can report a single consolidated grade.

        Without this, the progress tab in the LMS would show an expected grade
        from each possible child, rather than the n chosen child[ren].
        """
        return list(self._get_selected_child_blocks())


@XBlock.wants('user')
class LibraryContentDescriptor(LibraryContentFields, MakoModuleDescriptor, XmlDescriptor, StudioEditableDescriptor):
    """
    Descriptor class for LibraryContentModule XBlock.
    """
    module_class = LibraryContentModule
    mako_template = 'widgets/metadata-edit.html'
    js = {'coffee': [resource_string(__name__, 'js/src/vertical/edit.coffee')]}
    js_module_name = "VerticalDescriptor"

    @XBlock.handler
    def refresh_children(self, request, suffix):  # pylint: disable=unused-argument
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
        root_children = []

        store = self.system.modulestore
        with store.bulk_operations(self.location.course_key):
            # Currently, ALL children are essentially deleted and then re-added
            # in a way that preserves their block_ids (and thus should preserve
            # student data, grades, analytics, etc.)
            # Once course-level field overrides are implemented, this will
            # change to a more conservative implementation.

            # First, delete all our existing children to avoid block_id conflicts when we add them:
            for child in self.children:  # pylint: disable=access-member-before-definition
                store.delete_item(child, user_id)

            # Now add all matching children, and record the library version we use:
            new_libraries = []
            for library_key, old_version in self.source_libraries:  # pylint: disable=unused-variable
                library = _get_library(self.system.modulestore, library_key)  # pylint: disable=protected-access

                def copy_children_recursively(from_block):
                    """
                    Internal method to copy blocks from the library recursively
                    """
                    new_children = []
                    for child_key in from_block.children:
                        child = store.get_item(child_key, depth=9)
                        # We compute a block_id for each matching child block found in the library.
                        # block_ids are unique within any branch, but are not unique per-course or globally.
                        # We need our block_ids to be consistent when content in the library is updated, so
                        # we compute block_id as a hash of three pieces of data:
                        unique_data = "{}:{}:{}".format(
                            self.location.block_id,  # Must not clash with other usages of the same library in this course
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
                        new_child_info = store.create_item(
                            user_id,
                            self.location.course_key,
                            child_key.block_type,
                            block_id=child_block_id,
                            definition_locator=child.definition_locator,
                            runtime=self.system,
                            fields=fields,
                        )
                        new_children.append(new_child_info.location)
                    return new_children
                root_children.extend(copy_children_recursively(from_block=library))
                new_libraries.append(LibraryVersionReference(library_key, library.location.library_key.version_guid))
            self.source_libraries = new_libraries
            self.children = root_children  # pylint: disable=attribute-defined-outside-init
            self.system.modulestore.update_item(self, user_id)
        return Response()

    def has_dynamic_children(self):
        """
        Inform the runtime that our children vary per-user.
        See get_child_descriptors() above
        """
        return True

    def get_content_titles(self):
        """
        Returns list of friendly titles for our selected children only; without
        thi, all possible children's titles would be seen in the sequence bar in
        the LMS.

        This overwrites the get_content_titles method included in x_module by default.
        """
        titles = []
        for child in self._xmodule.get_child_descriptors():
            titles.extend(child.get_content_titles())
        return titles

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        """ XML support not yet implemented. """
        raise NotImplementedError

    def definition_to_xml(self, resource_fs):
        """ XML support not yet implemented. """
        raise NotImplementedError

    @classmethod
    def from_xml(cls, xml_data, system, id_generator):
        """ XML support not yet implemented. """
        raise NotImplementedError

    def export_to_xml(self, resource_fs):
        """ XML support not yet implemented. """
        raise NotImplementedError
