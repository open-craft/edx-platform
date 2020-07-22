

class PluginDiscussions(object):
    """
    The PluginDiscussions enum defines dictionary field names (and defaults)
    that can be specified by a Plugin App in order to configure itself as
    a discussion tool.
    """

    CONFIG = u"discussions"
    # A friendly name to show in the UI
    FRIENDLY_NAME = u"friendly_name"
    # An introductory description of the tool
    DESCRIPTION = u"description"
    # Icon to display in UI
    ICON = u"icon"
    # The capabilities this integration supports
    CAPABILITIES = u"capabilities"
    # The path to the API class which exposes discussion API functionality
    API_PATH = u"api_path"

    class Capabilities:
        """ Enum that lists capabilities supported by a discussion tool. """
        LTI1p1 = u"lti1.1"
        LTI1p3 = u"lti1.3"
        IN_CONTEXT_DISCUSSIONS = u"in_context_discussions"
        NOTIFICATIONS = u"notifications"
        COHORTS = u"cohort_aware"
