"""
django admin pages for certificates models
"""


from operator import itemgetter

from config_models.admin import ConfigurationModelAdmin
from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from organizations.api import get_organizations

from lms.djangoapps.certificates.models import (
    AllowListGenerationConfiguration,
    CertificateGenerationConfiguration,
    CertificateGenerationCourseSetting,
    CertificateHtmlViewConfiguration,
    CertificateTemplate,
    CertificateTemplateAsset,
    GeneratedCertificate
)


class CertificateTemplateForm(forms.ModelForm):
    """
    Django admin form for CertificateTemplate model
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organizations = get_organizations()
        org_choices = [(org["id"], org["name"]) for org in organizations]
        org_choices.insert(0, ('', 'None'))
        self.fields['organization_id'] = forms.TypedChoiceField(
            choices=org_choices, required=False, coerce=int, empty_value=None
        )
        languages = list(settings.CERTIFICATE_TEMPLATE_LANGUAGES.items())
        lang_choices = sorted(languages, key=itemgetter(1))
        lang_choices.insert(0, (None, 'All Languages'))
        self.fields['language'] = forms.ChoiceField(
            choices=lang_choices, required=False
        )

    class Meta(object):
        model = CertificateTemplate
        fields = '__all__'


class CertificateTemplateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplate model
    """
    list_display = ('name', 'description', 'organization_id', 'course_key', 'mode', 'language', 'is_active')
    form = CertificateTemplateForm


class CertificateTemplateAssetAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplateAsset model
    """

    list_display = ('description', 'asset_slug',)
    prepopulated_fields = {"asset_slug": ("description",)}

    # see PROD-1153 for the details
    def changelist_view(self, request, extra_context=None):
        if '.stage.edx.org' in request.get_host():
            extra_context = {'title': mark_safe('Select Certificate Template Asset to change <br/><br/>'
                                                '<div><strong style="color: red;"> Warning!</strong> Updating '
                                                'stage asset would also update production asset</div>')}
        return super().changelist_view(request, extra_context=extra_context)


class GeneratedCertificateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for GeneratedCertificate model
    """
    raw_id_fields = ('user',)
    show_full_result_count = False
    search_fields = ('course_id', 'user__username')
    list_display = ('id', 'course_id', 'mode', 'user')


class CertificateGenerationCourseSettingAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateGenerationCourseSetting model
    """
    list_display = ('course_key', 'self_generation_enabled', 'language_specific_templates_enabled')
    search_fields = ('course_key',)
    show_full_result_count = False


@admin.register(AllowListGenerationConfiguration)
class AllowListGenerationConfigurationAdmin(ConfigurationModelAdmin):
    pass

admin.site.register(CertificateGenerationConfiguration)
admin.site.register(CertificateGenerationCourseSetting, CertificateGenerationCourseSettingAdmin)
admin.site.register(CertificateHtmlViewConfiguration, ConfigurationModelAdmin)
admin.site.register(CertificateTemplate, CertificateTemplateAdmin)
admin.site.register(CertificateTemplateAsset, CertificateTemplateAssetAdmin)
admin.site.register(GeneratedCertificate, GeneratedCertificateAdmin)
