from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from django import forms
from django.http import Http404

from student import forms as student_forms

from openedx.core.djangoapps.course_groups import cohorts
from openedx.core.djangoapps.course_groups.models import CourseUserGroup


class CohortUsersAPIForm(forms.Form):
    """
    A form to validate 'course_id' and the 'cohort_id' of the course corresponding to the 'course_id'.
    """
    course_key_string = forms.CharField()
    cohort_id = forms.IntegerField()
    username = forms.CharField(required=False)

    def clean_course_key_string(self):
        course_key_string = self.cleaned_data['course_key_string']

        try:
            course_key = CourseKey.from_string(course_key_string)
            self.cleaned_data['course_key'] = course_key
            return course_key_string
        except InvalidKeyError:
            raise forms.ValidationError('{} is not a valid course key'.format(course_key_string))

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if username:
            student_forms.validate_username(username)
            return username

    def clean(self):
        cleaned_data = super(CohortUsersAPIForm, self).clean()
        if cleaned_data.get('course_key'):
            course_key = cleaned_data['course_key']
            cohort_id = cleaned_data['cohort_id']

            try:
                cohort = cohorts.get_cohort_by_id(course_key, cohort_id)
                cleaned_data['cohort'] = cohort
            except CourseUserGroup.DoesNotExist:
                raise Http404(
                    "Cohort (ID {cohort_id}) not found for {course_key_string}".format(
                        cohort_id=cohort_id,
                        course_key_string=cleaned_data['course_key_string']
                    )
                )
