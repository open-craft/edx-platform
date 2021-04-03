"""
This module contains various configuration settings via
waffle switches for third party authentication.
"""


from edx_toggles.toggles.__future__ import WaffleSwitch


WAFFLE_NAMESPACE = 'third_party_auth'

# .. toggle_name: ALWAYS_ASSOCIATE_USER_BY_EMAIL
# .. toggle_implementation: WaffleSwitch
# .. toggle_default: False
# .. toggle_description: Always associates current social auth user with
#   the user with the same email address in the database, which verifies
#   that only a single database user is associated with the email.
# .. toggle_use_cases: opt_in
# .. toggle_creation_date: 2020-12-23
# .. toggle_tickets: https://openedx.atlassian.net/browse/OSPR-5312
ALWAYS_ASSOCIATE_USER_BY_EMAIL = WaffleSwitch(
    f'{WAFFLE_NAMESPACE}.always_associate_user_by_email',
    module_name=__name__,
)
