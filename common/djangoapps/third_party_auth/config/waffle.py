"""
This module contains various configuration settings via
waffle switches for third party authentication.
"""


from openedx.core.djangoapps.waffle_utils import WaffleSwitch


WAFFLE_NAMESPACE = 'third_party_auth'

ALWAYS_ASSOCIATE_USER_BY_EMAIL = WaffleSwitch(
    WAFFLE_NAMESPACE,
    'always_associate_user_by_email',
)
