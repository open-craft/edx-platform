"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from django.utils import translation
from xblock.core import XBlock
from xblock.fields import Scope, Integer
from web_fragments.fragment import Fragment
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from xmodule.raw_module import RawDescriptor
from xmodule.xml_module import XmlParserMixin

# FIXME: move these
from xmodule.video_module.video_xfields import VideoFields
from xmodule.video_module.video_utils import create_youtube_string


# FIXME XXX debugging only
import logging
LOG = logging.getLogger(__name__)


class VideoXBlock(VideoFields, XBlock, StudioEditableXBlockMixin, XmlParserMixin):
    """
    TO-DO: document what your XBlock does.
    """

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # TO-DO: delete count, and define your own fields.
    count = Integer(
        default=0, scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )

    editable_fields = (
        'display_name', 
        'youtube_id_1_0', 'youtube_id_0_75', 'youtube_id_1_25', 'youtube_id_1_5',
        'start_time', 'end_time',
        'source', 'download_video', 'html5_sources',
        'track', 'download_track', 'sub', 'show_captions', 'transcripts',
        'handout', 'only_on_web',
        'edx_video_id',
    )

    # support for legacy OLX format - consumed by XmlParserMixin.load_metadata
    metadata_translations = dict(RawDescriptor.metadata_translations)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the VideoXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/xblock_video.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/xblock_video.css"))

        # Add i18n js
        statici18n_js_url = self._get_statici18n_js_url()
        if statici18n_js_url:
            frag.add_javascript_url(self.runtime.local_resource_url(self, statici18n_js_url))

        frag.add_javascript(self.resource_string("static/js/src/xblock_video.js"))
        frag.initialize_js('VideoXBlock')
        return frag

    # TO-DO: change this handler to perform your own actions.  You may need more
    # than one handler, or you may not need any handlers at all.
    @XBlock.json_handler
    def increment_count(self, data, suffix=''):
        """
        An example handler, which increments the data.
        """
        # Just to show data coming in...
        assert data['hello'] == 'world'

        self.count += 1
        return {"count": self.count}

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("VideoXBlock",
             """<video-xblock/>
             """),
            ("Multiple VideoXBlock",
             """<vertical_demo>
                <video-xblock/>
                <video-xblock/>
                <video-xblock/>
                </vertical_demo>
             """),
        ]

    @staticmethod
    def _get_statici18n_js_url():
        """
        Returns the Javascript translation file for the currently selected language, if any.
        Defaults to English if available.
        """
        locale_code = translation.get_language()
        if locale_code is None:
            return None
        text_js = 'public/js/translations/{locale_code}/text.js'
        lang_code = locale_code.split('-')[0]
        for code in (locale_code, lang_code, 'en'):
            loader = ResourceLoader(__name__)
            if pkg_resources.resource_exists(
                    loader.module_name, text_js.format(locale_code=code)):
                return text_js.format(locale_code=code)
        return None

    @staticmethod
    def get_dummy():
        """
        Dummy method to generate initial i18n
        """
        return translation.gettext_noop('Dummy')

    @classmethod
    def _apply_translations_to_node_attributes(cls, block, node):
        """
        Applies metadata translations for attributes stored on an inlined XML element.
        """
        for old_attr, target_attr in cls.metadata_translations.iteritems():
            if old_attr in node.attrib and hasattr(block, target_attr):
                setattr(block, target_attr, node.attrib[old_attr])

    @classmethod
    def _apply_metadata_and_policy(cls, block, node, runtime):
        """
        Attempt to load definition XML from "video" folder in OLX, than parse it and update block fields
        """
        try:
            LOG.debug("_apply_metadata_and_policy(%s, %s, %s, %s)", cls, block, node, runtime)
            node.tag = 'video'
            definition_xml, _ = cls.load_definition_xml(node, runtime, block.scope_ids.def_id)
        except Exception as err:  # pylint: disable=broad-except
            log.info(
                "Exception %s when trying to load definition xml for block %s - assuming XBlock export format",
                err,
                block
            )
            return

        metadata = cls.load_metadata(definition_xml)
        cls.apply_policy(metadata, runtime.get_policy(block.scope_ids.usage_id))

        for field_name, value in metadata.iteritems():
            if field_name in block.fields:
                setattr(block, field_name, value)

        # FIXME: handle parsing XBlock asides?
