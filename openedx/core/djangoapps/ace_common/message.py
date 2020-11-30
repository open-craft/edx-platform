"""
Base Message types to be used to construct ace messages.
"""


from edx_ace.message import MessageType

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


class BaseMessageType(MessageType):
    def __init__(self, *args, **kwargs):
        super(BaseMessageType, self).__init__(*args, **kwargs)
