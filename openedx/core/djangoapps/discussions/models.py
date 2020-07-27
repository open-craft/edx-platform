from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from opaque_keys.edx.django.models import LearningContextKeyField

from openedx.core.djangoapps.config_model_utils.models import CourseAppConfigOptionsModel
from openedx.core.djangoapps.discussions.discussions_apps import DiscussionAppsPluginManager


def _get_provider_choices():
    return [
        (provider.name, provider.friendly_name)
        for provider in DiscussionAppsPluginManager.get_enabled_discussion_apps()
    ]


class DiscussionConfig(CourseAppConfigOptionsModel):
    """
    Configuration model to store configuration for Discussions applications.
    """

    provider = models.CharField(
        blank=False,
        db_index=True,
        max_length=100,
        verbose_name=_("Discussion provider"),
        help_text=_("The discussion tool/provider."),
        null=False,
        choices=_get_provider_choices(),
    )
    config = JSONField(
        blank=True,
        default={},
        help_text=_("The discussion configuration data that can be user visible."),
    )
    private_config = JSONField(
        blank=True,
        default={},
        help_text=_(
            "The discussion configuration data that contains secret information"
            "such as OAuth keys etc and should not be available to users."
        ),
    )


class LearningContextDiscussionConfig(models.Model):
    """
    Associates each learning context with a :class:`DiscussionConfiguration` via the slug.
    """

    context_key = LearningContextKeyField(
        primary_key=True,
        db_index=True,
        unique=True,
        max_length=255,
        verbose_name=_("Learning Context"),
    )
    config_slug = models.CharField(
        blank=False,
        max_length=100,
        verbose_name=_("Configuration slug"),
        help_text=_("Should be an existing slug from a DiscussionConfig"),
    )

    def __str__(self):
        return "Using config with slug {config_slug} for {context_key}".format(
            context_key=self.context_key,
            config_slug=self.config_slug,
        )
