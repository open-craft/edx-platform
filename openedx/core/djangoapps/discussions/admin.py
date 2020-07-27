from config_models.admin import KeyedConfigurationModelAdmin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import DiscussionConfig, LearningContextDiscussionConfig


class DiscussionConfigAdminModel(KeyedConfigurationModelAdmin):
    search_fields = ("site", "org", "org_course", "context_key", "slug", "name", "description", "discussion_provider")
    fieldsets = (
        (_("Key settings"), {
            "fields": ("enabled", "slug", "provider",),
            "description": _("These settings should never be changed once set!"),
        }),
        (_("Name and Description"), {
            "fields": ("name", "description"),
            "description": _("The name and description can be visible to Course Authors, make them useful.")
        }),
        (_("Scope"), {
            "fields": ("site", "org", "org_course", "context_key"),
            "description":
                _("The scope set here will define where all this configuration can be used."
                  "If nothing is set the config is available globally. If only a site is set"
                  "then the configuration is only available to learning contexts (courses "
                  "for instance) in that site. Only of these can be set at a time."
                  "DO NOT EDIT ONCE SET!")
        }),
        (_("Configuration"), {
            "fields": ("config", "private_config")
        }),
    )


admin.site.register(DiscussionConfig, DiscussionConfigAdminModel)
admin.site.register(LearningContextDiscussionConfig)
