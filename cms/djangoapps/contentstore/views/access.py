""" Helper methods for determining user access permissions in Studio """

from opaque_keys.edx.locator import LibraryLocator
from student.roles import (
    GlobalStaff, CourseStaffRole, CourseInstructorRole, LibraryUserRole,
    OrgStaffRole, OrgInstructorRole, OrgLibraryUserRole
)
from student import auth


# Studio permissions:
EDIT_ROLES = 8
VIEW_USERS = 4
EDIT_CONTENT = 2
VIEW_CONTENT = 1
# In addition to the above, one is always allowed to "demote" oneself to a lower role within a course, or remove oneself.


def get_user_permissions(user, course_key, org=None):
    """
    Get the set() of permissions that this user has in the given course context.
    Can also set course_key=None and pass in an org to get the user's
    permissions for that organization as a whole.

    These permissions are specific to studio, but the roles that define them are
    shared with the LMS.
    """
    if org is None:
        org = course_key.org
        course_key = course_key.for_branch(None)
    else:
        assert course_key is None
    all_perms = {EDIT_ROLES, VIEW_USERS, EDIT_CONTENT, VIEW_CONTENT}
    # global staff, org instructors, and course instructors have all permissions:
    if GlobalStaff().has_user(user) or OrgInstructorRole(org=org).has_user(user):
        return all_perms
    if course_key and auth.has_access(user, CourseInstructorRole(course_key)):
        return all_perms
    # Staff have a all permissions except EDIT_ROLES:
    if OrgStaffRole(org=org).has_user(user) or (course_key and auth.has_access(user, CourseStaffRole(course_key))):
        return {VIEW_USERS, EDIT_CONTENT, VIEW_CONTENT}
    # Otherwise, for libraries, users can view only:
    if (course_key and isinstance(course_key, LibraryLocator)):
        if OrgLibraryUserRole(org=org).has_user(user) or auth.has_access(user, LibraryUserRole(course_key)):
            return {VIEW_USERS, VIEW_CONTENT}
    return set()


def has_course_access(user, course_key, role=CourseStaffRole):
    """
    Return True if user allowed to access this course_id
    Note that the CMS permissions model is with respect to courses
    There is a super-admin permissions if user.is_staff is set
    Also, since we're unifying the user database between LMS and CAS,
    I'm presuming that the course instructor (formally known as admin)
    will not be in both INSTRUCTOR and STAFF groups, so we have to cascade our
    queries here as INSTRUCTOR has all the rights that STAFF do
    """
    if GlobalStaff().has_user(user):
        return True
    if OrgInstructorRole(org=course_key.org).has_user(user):
        return True
    if OrgStaffRole(org=course_key.org).has_user(user):
        return True
    # temporary to ensure we give universal access given a course until we impl branch specific perms
    return auth.has_access(user, role(course_key.for_branch(None)))


def has_write_access(user, course_key):
    """
    Return True iff user is allowed to modify the given course/library.
    Currently equivalent to has_course_access but less amibguously named.
    """
    return EDIT_CONTENT in get_user_permissions(user, course_key)


def has_read_access(user, course_key):
    """
    Return True iff user is allowed to view this course/library.

    There is currently no such thing as read-only course access in studio, but
    there is read-only access to content libraries.
    """
    return VIEW_CONTENT in get_user_permissions(user, course_key)


def get_user_role(user, course_id):
    """
    What type of access: staff or instructor does this user have in Studio?

    No code should use this for access control, only to quickly serialize the type of access
    where this code knows that Instructor trumps Staff and assumes the user has one or the other.

    This will not return student role because its purpose for using in Studio.

    :param course_id: the course_id of the course we're interested in
    """
    # afaik, this is only used in lti
    if auth.has_access(user, CourseInstructorRole(course_id)):
        return 'instructor'
    else:
        return 'staff'
