from django.core.exceptions import ValidationError
from django.forms import CharField, Form

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from student import forms as student_forms


class CourseEnrollmentsByUsernameOrCourseIDListForm(Form):
    """
    A form that validates the query string parameters for the CourseEnrollmentsByUsernameOrCourseIDListView.
    """
    username = CharField(required=False)
    course_id = CharField(required=False)

    def clean_course_id(self):
        """
        Validate and return a course ID.
        """
        course_id = self.cleaned_data.get('course_id')
        if course_id:
            try:
                return CourseKey.from_string(course_id)
            except InvalidKeyError:
                raise ValidationError("'{}' is not a valid course id.".format(course_id))
        return course_id

    def clean_username(self):
        """
        Validate a string of comma-separated usernames and return a list of usernames.
        """
        usernames_csv_string = self.cleaned_data.get('username')
        if usernames_csv_string:
            usernames = usernames_csv_string.split(',')
            for username in usernames:
                student_forms.validate_username(username)
            return usernames
        return usernames_csv_string

    def clean(self):
        """
        Validate if at least one of course_id or username field is present and return the validated data.
        """

        cleaned_data = super(CourseEnrollmentsByUsernameOrCourseIDListForm, self).clean()

        if not self.errors:
            course_id = cleaned_data.get('course_id')
            username = cleaned_data.get('username')

            if not course_id and not username:
                raise ValidationError(
                    "At least one of 'course_id', 'username' query string parameters is required."
                )
        return cleaned_data
