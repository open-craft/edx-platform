"""
Test for the XBlock serialization lib's API
"""
from xml.etree import ElementTree

from openedx.core.djangolib.testing.utils import skip_unless_cms
from xmodule.modulestore.django import contentstore, modulestore
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase, upload_file_to_course
from xmodule.modulestore.tests.factories import BlockFactory, CourseFactory, ToyCourseFactory
from xmodule.util.sandboxing import DEFAULT_PYTHON_LIB_FILENAME

from . import api


# The expected OLX string for the 'Toy_Videos' sequential in the toy course
EXPECTED_SEQUENTIAL_OLX = """
<sequential display_name="Toy Videos" format="Lecture Sequence" url_name="Toy_Videos">
  <html url_name="secret:toylab" display_name="Toy lab"><![CDATA[
<b>Lab 2A: Superposition Experiment</b>


<p>Isn't the toy course great?</p>

<p>Let's add some markup that uses non-ascii characters.
'For example, we should be able to write words like encyclop&aelig;dia, or foreign words like fran&ccedil;ais.
Looking beyond latin-1, we should handle math symbols:  &pi;r&sup2 &le; &#8734.
And it shouldn't matter if we use entities or numeric codes &mdash; &Omega; &ne; &pi; &equiv; &#937; &#8800; &#960;.
</p>


]]></html>
  <html url_name="toyjumpto" display_name="Text"><![CDATA[
<a href="/jump_to_id/vertical_test">This is a link to another page and some Chinese 四節比分和七年前</a> <p>Some more Chinese 四節比分和七年前</p>

]]></html>
  <html url_name="toyhtml" display_name="Text"><![CDATA[
<a href='/static/handouts/sample_handout.txt'>Sample</a>
]]></html>
  <html url_name="nonportable" display_name="Text"><![CDATA[
<a href="/static/foo.jpg">link</a>

]]></html>
  <html url_name="nonportable_link" display_name="Text"><![CDATA[
<a href="/jump_to_id/nonportable_link">link</a>


]]></html>
  <html url_name="badlink" display_name="Text"><![CDATA[
<img src="/static//file.jpg" />

]]></html>
  <html url_name="with_styling" display_name="Text"><![CDATA[
<p style="font:italic bold 72px/30px Georgia, serif; color: red; ">Red text here</p>
]]></html>
  <html url_name="just_img" display_name="Text"><![CDATA[
<img src="/static/foo_bar.jpg" />
]]></html>
  <video
    display_name="Video Resources"
    url_name="Video_Resources"
    youtube="1.00:1bK-WdDi6Qw"
    youtube_id_1_0="1bK-WdDi6Qw"
  />
</sequential>
"""


EXPECTED_OPENASSESSMENT_OLX = """
<openassessment
    submission_start="2001-01-01T00:00"
    submission_due="2029-01-01T00:00"
    text_response="required"
    text_response_editor="text"
    allow_multiple_files="True"
    allow_latex="False"
    prompts_type="text"
    teams_enabled="False"
    selected_teamset_id=""
    show_rubric_during_response="False"
>
  <title>Open Response Assessment</title>
  <assessments>
    <assessment name="student-training">
      <example>
        <answer>
          <part>Replace this text with your own sample response for this assignment. Then, under Response Score to the right, select an option for each criterion. Learners practice performing peer assessments by assessing this response and comparing the options that they select in the rubric with the options that you specified.</part>
        </answer>
        <select criterion="Ideas" option="Fair"/>
        <select criterion="Content" option="Good"/>
      </example>
      <example>
        <answer>
          <part>Replace this text with another sample response, and then specify the options that you would select for this response.</part>
        </answer>
        <select criterion="Ideas" option="Poor"/>
        <select criterion="Content" option="Good"/>
      </example>
    </assessment>
    <assessment name="peer-assessment" must_grade="5" must_be_graded_by="3" enable_flexible_grading="False" start="2001-01-01T00:00" due="2029-01-01T00:00"/>
    <assessment name="self-assessment" start="2001-01-01T00:00" due="2029-01-01T00:00"/>
    <assessment name="staff-assessment" start="2001-01-01T00:00" due="2029-01-01T00:00" required="False"/>
  </assessments>
  <prompts>
    <prompt>
      <description>
    Censorship in the Libraries

    'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author

    Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.

    Read for conciseness, clarity of thought, and form.
</description>
    </prompt>
  </prompts>
  <rubric>
    <criterion feedback="optional">
      <name>Ideas</name>
      <label>Ideas</label>
      <prompt>Determine if there is a unifying theme or main idea.</prompt>
      <option points="0">
        <name>Poor</name>
        <label>Poor</label>
        <explanation>Difficult for the reader to discern the main idea.  Too brief or too repetitive to establish or maintain a focus.</explanation>
      </option>
      <option points="3">
        <name>Fair</name>
        <label>Fair</label>
        <explanation>Presents a unifying theme or main idea, but may include minor tangents.  Stays somewhat focused on topic and task.</explanation>
      </option>
      <option points="5">
        <name>Good</name>
        <label>Good</label>
        <explanation>Presents a unifying theme or main idea without going off on tangents.  Stays completely focused on topic and task.</explanation>
      </option>
    </criterion>
    <criterion>
      <name>Content</name>
      <label>Content</label>
      <prompt>Assess the content of the submission</prompt>
      <option points="0">
        <name>Poor</name>
        <label>Poor</label>
        <explanation>Includes little information with few or no details or unrelated details.  Unsuccessful in attempts to explore any facets of the topic.</explanation>
      </option>
      <option points="1">
        <name>Fair</name>
        <label>Fair</label>
        <explanation>Includes little information and few or no details.  Explores only one or two facets of the topic.</explanation>
      </option>
      <option points="3">
        <name>Good</name>
        <label>Good</label>
        <explanation>Includes sufficient information and supporting details. (Details may not be fully developed; ideas may be listed.)  Explores some facets of the topic.</explanation>
      </option>
      <option points="5">
        <name>Excellent</name>
        <label>Excellent</label>
        <explanation>Includes in-depth information and exceptional supporting details that are fully developed.  Explores all facets of the topic.</explanation>
      </option>
    </criterion>
    <feedbackprompt>
(Optional) What aspects of this response stood out to you? What did it do well? How could it be improved?
</feedbackprompt>
    <feedback_default_text>
I think that this response...
</feedback_default_text>
  </rubric>
</openassessment>
"""


@skip_unless_cms
class XBlockSerializationTestCase(SharedModuleStoreTestCase):
    """
    Test for the XBlock serialization library's python API
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up a course for use in these tests
        """
        super().setUpClass()
        cls.course = ToyCourseFactory.create()

    def assertXmlEqual(self, xml_str_a: str, xml_str_b: str) -> None:
        """ Assert that the given XML strings are equal, ignoring attribute order and some whitespace variations. """
        self.assertEqual(
            ElementTree.canonicalize(xml_str_a, strip_text=True),
            ElementTree.canonicalize(xml_str_b, strip_text=True),
        )

    def test_html_with_static_asset(self):
        """
        Test that HTML gets converted to use CDATA and static assets are
        handled.
        """
        block_id = self.course.id.make_usage_key('html', 'just_img')  # see sample_courses.py
        html_block = modulestore().get_item(block_id)
        serialized = api.serialize_xblock_to_olx(html_block)

        self.assertXmlEqual(
            serialized.olx_str,
            """
            <html display_name="Text" url_name="just_img"><![CDATA[
                <img src="/static/foo_bar.jpg" />
            ]]></html>
            """
        )
        self.assertIn("CDATA", serialized.olx_str)
        self.assertEqual(serialized.static_files, [
            api.StaticFile(
                name="foo_bar.jpg",
                url="/asset-v1:edX+toy+2012_Fall+type@asset+block@foo_bar.jpg",
                data=None,
            ),
        ])

    def test_html_with_static_asset_blockstore(self):
        """
        Test the blockstore-specific serialization of an HTML block
        """
        block_id = self.course.id.make_usage_key('html', 'just_img')  # see sample_courses.py
        html_block = modulestore().get_item(block_id)
        serialized = api.serialize_xblock_to_olx(html_block)
        serialized_blockstore = api.serialize_modulestore_block_for_blockstore(html_block)
        self.assertXmlEqual(
            serialized_blockstore.olx_str,
            # For blockstore, OLX should never contain "url_name" as that ID is specified by the filename:
            """
            <html display_name="Text"><![CDATA[
                <img src="/static/foo_bar.jpg" />
            ]]></html>
            """
        )
        self.assertIn("CDATA", serialized.olx_str)
        # Static files should be identical:
        self.assertEqual(serialized.static_files, serialized_blockstore.static_files)
        # This is the only other difference - an extra field with the blockstore-specific definition ID:
        self.assertEqual(serialized_blockstore.def_id, "html/just_img")

    def test_html_with_fields(self):
        """ Test an HTML Block with non-default fields like editor='raw' """
        course = CourseFactory.create(display_name='test course', run="Testing_course")
        html_block = BlockFactory.create(
            parent_location=course.location,
            category="html",
            display_name="Non-default HTML Block",
            editor="raw",
            use_latex_compiler=True,
            data="🍔",
        )
        serialized = api.serialize_xblock_to_olx(html_block)
        self.assertXmlEqual(
            serialized.olx_str,
            """
            <html
                url_name="Non-default_HTML_Block"
                display_name="Non-default HTML Block"
                editor="raw"
                use_latex_compiler="true"
            ><![CDATA[
                🍔
            ]]></html>
            """
        )

    def test_export_sequential(self):
        """
        Export a sequential from the toy course, including all of its children.
        """
        sequential_id = self.course.id.make_usage_key('sequential', 'Toy_Videos')  # see sample_courses.py
        sequential = modulestore().get_item(sequential_id)
        serialized = api.serialize_xblock_to_olx(sequential)

        self.assertXmlEqual(serialized.olx_str, EXPECTED_SEQUENTIAL_OLX)

    def test_export_sequential_blockstore(self):
        """
        Export a sequential from the toy course, formatted for blockstore.
        """
        sequential_id = self.course.id.make_usage_key('sequential', 'Toy_Videos')  # see sample_courses.py
        sequential = modulestore().get_item(sequential_id)
        serialized = api.serialize_modulestore_block_for_blockstore(sequential)

        self.assertXmlEqual(serialized.olx_str, """
            <sequential display_name="Toy Videos" format="Lecture Sequence">
                <xblock-include definition="html/secret:toylab"/>
                <xblock-include definition="html/toyjumpto"/>
                <xblock-include definition="html/toyhtml"/>
                <xblock-include definition="html/nonportable"/>
                <xblock-include definition="html/nonportable_link"/>
                <xblock-include definition="html/badlink"/>
                <xblock-include definition="html/with_styling"/>
                <xblock-include definition="html/just_img"/>
                <xblock-include definition="video/Video_Resources"/>
            </sequential>
        """)

    def test_capa_python_lib(self):
        """ Test capa problem blocks with and without python_lib.zip """
        course = CourseFactory.create(display_name='Python Testing course', run="PY")
        upload_file_to_course(
            course_key=course.id,
            contentstore=contentstore(),
            source_file='./common/test/data/uploads/python_lib.zip',
            target_filename=DEFAULT_PYTHON_LIB_FILENAME,
        )

        regular_problem = BlockFactory.create(
            parent_location=course.location,
            category="problem",
            display_name="Problem No Python",
            max_attempts=3,
            data="<problem><optionresponse></optionresponse></problem>",
        )

        python_problem = BlockFactory.create(
            parent_location=course.location,
            category="problem",
            display_name="Python Problem",
            data='<problem>This uses python: <script type="text/python">...</script>...</problem>',
        )

        # The regular problem doesn't use python so shouldn't contain python_lib.zip:

        serialized = api.serialize_xblock_to_olx(regular_problem)
        assert not serialized.static_files
        self.assertXmlEqual(
            serialized.olx_str,
            """
            <problem display_name="Problem No Python" url_name="Problem_No_Python" max_attempts="3">
                <optionresponse></optionresponse>
            </problem>
            """
        )

        # The python problem should contain python_lib.zip:

        serialized = api.serialize_xblock_to_olx(python_problem)
        assert len(serialized.static_files) == 1
        assert serialized.static_files[0].name == "python_lib.zip"
        self.assertXmlEqual(
            serialized.olx_str,
            """
            <problem display_name="Python Problem" url_name="Python_Problem">
                This uses python: <script type="text/python">...</script>...
            </problem>
            """
        )

    def test_jsinput_extra_files(self):
        """
        Test JSInput problems with extra static files.
        """
        course = CourseFactory.create(display_name='JSInput Testing course', run="JSI")
        jsinput_files = [
            ("simple-question.html", "./common/test/data/uploads/simple-question.html"),
            ("simple-question.js", "./common/test/data/uploads/simple-question.js"),
            ("simple-question.css", "./common/test/data/uploads/simple-question.css"),
            ("image.jpg", "./common/test/data/uploads/image.jpg"),
            ("jschannel.js", "./common/static/js/capa/src/jschannel.js"),
        ]
        for filename, full_path in jsinput_files:
            upload_file_to_course(
                course_key=course.id,
                contentstore=contentstore(),
                source_file=full_path,
                target_filename=filename,
            )

        jsinput_problem = BlockFactory.create(
            parent_location=course.location,
            category="problem",
            display_name="JSInput Problem",
            data="<problem><jsinput html_file='/static/simple-question.html' /></problem>",
        )

        # The jsinput problem should contain the html_file along with extra static files:

        serialized = api.serialize_xblock_to_olx(jsinput_problem)
        assert len(serialized.static_files) == 5
        for file in serialized.static_files:
            self.assertIn(file.name, list(map(lambda f: f[0], jsinput_files)))

        self.assertXmlEqual(
            serialized.olx_str,
            """
            <problem display_name="JSInput Problem" url_name="JSInput_Problem">
                <jsinput html_file='/static/simple-question.html' />
            </problem>
            """
        )

    def test_url_name_inserted(self):
        """
        Ensures that XBlockSerializer adds a url_name attribute for block classes that don't provide it.
        """
        discussion_id = self.course.id.make_usage_key('discussion', 'Toy_forum')
        discussion = modulestore().get_item(discussion_id)
        serialized = api.serialize_xblock_to_olx(discussion)
        self.assertXmlEqual(serialized.olx_str, """
            <discussion url_name="Toy_forum" xblock-family="xblock.v1" />
        """)
