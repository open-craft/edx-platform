"""
Library edit page in Studio
"""

from bok_choy.page_object import PageObject
from .container import XBlockWrapper
from ...tests.helpers import disable_animations
from .utils import confirm_prompt, wait_for_notification
from . import BASE_URL


class LibraryPage(PageObject):
    """
    Container page in Studio
    """

    def __init__(self, browser, locator):
        super(LibraryPage, self).__init__(browser)
        self.locator = locator

    @property
    def url(self):
        """
        URL to the library edit page page for the given library.
        """
        return "{}/library/{}".format(BASE_URL, unicode(self.locator))

    def is_browser_on_page(self):
        """
        Returns True iff the browser has loaded the library edit page.
        """
        return self.q(css='body.view-library').present

    def get_header_title(self):
        """
        The text of the main heading (H1) visible on the page.
        """
        return self.q(css='h1.page-header-title').text

    def wait_until_ready(self):
        """
        When the page first loads, there is a loading indicator and most
        functionality is not yet available. This waits for that loading to
        finish.

        Always call this before using the page. It also disables animations
        for improved test reliability.
        """
        self.wait_for_ajax()
        self.wait_for_element_invisibility('.ui-loading', 'Wait for the page to complete its initial loading of XBlocks via AJAX')
        disable_animations(self)

    def click_add_button(self, item_type, specific_type=None):
        """
        Click one of the "Add New Component" buttons.

        item_type should be "advanced", "html", "problem", or "video"

        specific_type is required for some types and should be something like
        "Blank Common Problem".
        """
        btn = self.q(css='.add-xblock-component .add-xblock-component-button[data-type={}]'.format(item_type))  # .first because sometimes there are two "Add New Component" blocks
        multiple_templates = btn.filter(lambda el: 'multiple-templates' in el.get_attribute('class')).present
        btn.click()
        if multiple_templates:
            sub_template_menu_div_selector = '.new-component-{}'.format(item_type)
            self.wait_for_element_visibility(sub_template_menu_div_selector, 'Wait for the templates sub-menu to appear')
            self.wait_for_element_invisibility('.add-xblock-component .new-component', 'Wait for the add component menu to disappear')
            #self.wait_for(lambda: 'overflow' not in self.q(css=sub_template_menu_div_selector).attrs("style"), 'Wait for the templates sub-menu animation to finish')

            all_options = self.q(css='.new-component-{} ul.new-component-template li a span'.format(item_type))
            chosen_option = all_options.filter(lambda el: el.text == specific_type).first
            chosen_option.click()
        wait_for_notification(self)
        self.wait_for_ajax()

    @property
    def xblocks(self):
        """
        Return a list of xblocks loaded on the container page.
        """
        return self._get_xblocks()

    def click_duplicate_button(self, xblock_id):
        """
        Click on the duplicate button for the given XBlock
        """
        self._action_btn_for_xblock_id(xblock_id, "duplicate").click()
        wait_for_notification(self)
        self.wait_for_ajax()

    def click_delete_button(self, xblock_id, confirm=True):
        """
        Click on the delete button for the given XBlock
        """
        self._action_btn_for_xblock_id(xblock_id, "delete").click()
        if confirm:
            confirm_prompt(self)  # this will also wait_for_notification()
            self.wait_for_ajax()

    def _get_xblocks(self):
        """
        Create an XBlockWrapper for each XBlock div found on the page.
        """
        prefix = '.wrapper-xblock.level-page '
        return self.q(css=prefix + XBlockWrapper.BODY_SELECTOR).map(lambda el: XBlockWrapper(self.browser, el.get_attribute('data-locator'))).results

    def _div_for_xblock_id(self, xblock_id):
        """
        Given an XBlock's usage locator as a string, return the WebElement for
        that block's wrapper div.
        """
        return self.q(css='.wrapper-xblock.level-page .studio-xblock-wrapper').filter(lambda el: el.get_attribute('data-locator') == xblock_id)

    def _action_btn_for_xblock_id(self, xblock_id, action):
        """
        Given an XBlock's usage locator as a string, return one of its action
        buttons.
        action is 'edit', 'duplicate', or 'delete'
        """
        return self._div_for_xblock_id(xblock_id)[0].find_element_by_css_selector('.header-actions .{action}-button.action-button'.format(action=action))
