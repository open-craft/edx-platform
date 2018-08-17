import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CharField, Form

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey


class BulkEnrollmentsListForm(Form):
    """
    TODO:
    """
    username = CharField(required=False)
    course_id = CharField(required=False)

    def clean_course_id(self):
        """
        TODO:
        """
        course_id_string = self.cleaned_data.get('course_id')
        if course_id_string:
            try:
                return CourseKey.from_string(course_id_string)
            except InvalidKeyError:
                raise ValidationError("'{}' is not a valid course key.".format(unicode(course_id_string)))

    def clean_username(self):
        """
        TODO:
        """
        usernames_string = self.cleaned_data.get('username')
        if usernames_string:
            username_regex = re.compile('^{}$'.format(settings.USERNAME_PATTERN))
            usernames = usernames_string.split(',')
            for username in usernames:
                if not username_regex.match(username):
                    raise ValidationError("'{}' is not a vallid username.".format(username))
            return usernames

    def clean(self):
        """
        TODO:
        """
        cleaned_data = super(BulkEnrollmentsListForm, self).clean()

        if not cleaned_data.get('course_id') and not cleaned_data.get('username'):
            raise ValidationError(
                "At least one of 'course_id', 'username' query string parameters is required."
            )
        return cleaned_data
