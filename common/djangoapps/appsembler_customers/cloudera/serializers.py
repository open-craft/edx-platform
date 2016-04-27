from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import serializers


class StringListField(serializers.CharField):
    """
    Custom Serializer for turning a comma delimited string into a list.
    """
    def to_native(self, data):
        if not data:
            return []

        items = data.split(',')
        return [item for item in items]

class BulkEnrollmentSerializer(serializers.Serializer):
    identifiers = StringListField(required=True)
    courses = StringListField(required=True)
    action = serializers.ChoiceField(
        choices=(
            ('enroll', 'enroll'),
            ('unenroll', 'unenroll')
        ),
        required=True
    )
    auto_enroll = serializers.BooleanField(default=False)
    email_students = serializers.BooleanField(default=False)

    def validate_courses(self, attrs, source):
        """
        Check that each course key in list is valid.
        """
        value = attrs[source]
        course_keys = value.split(',')
        for course in course_keys:
            try:
                CourseKey.from_string(course)
            except InvalidKeyError:
                raise serializers.ValidationError("Course key not valid: {}".format(course))
        return attrs
