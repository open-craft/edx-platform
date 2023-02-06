"""
Toggles for Dashboard page.
"""
from edx_toggles.toggles import WaffleSwitch

# Namespace for student waffle flags.
WAFFLE_FLAG_NAMESPACE = 'student'

# Waffle flag to enable control redirecting after enrolment.
# .. toggle_name: student.redirect_to_courseware_after_enrollment
# .. toggle_implementation: WaffleSwitch
# .. toggle_default: False
# .. toggle_description: Redirect to courseware after enrollment instead of dashboard.
# .. toggle_use_cases: open_edx
# .. toggle_creation_date: 2023-02-06
# .. toggle_target_removal_date: None
# .. toggle_warning: None
REDIRECT_TO_COURSEWARE_AFTER_ENROLLMENT = WaffleSwitch(
    f'{WAFFLE_FLAG_NAMESPACE}.redirect_to_courseware_after_enrollment', __name__
)


def should_redirect_to_courseware_after_enrollment():
    return REDIRECT_TO_COURSEWARE_AFTER_ENROLLMENT.is_enabled()
