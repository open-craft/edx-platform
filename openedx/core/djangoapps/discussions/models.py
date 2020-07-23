from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from opaque_keys.edx.django.models import LearningContextKeyField

from openedx.core.djangoapps.config_model_utils.models import CourseAppConfigOptionsModel


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
        blank=False,
        null=False,
    )
    config = JSONField(
        blank=False,
        default={},
        help_text=_("The discussion configuration data that can be user visible."),
        default={},
    )
    private_config = JSONField(
        blank=False,
        default={},
        help_text=_(
            "The discussion configuration data that contains secret information"
            "such as OAuth keys etc and should not be available to users."
        ),
        default={},
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
        verbose_name=_("Unique configuration slug"),
        help_text=_("A unique identifier for this configuration."),
    )
