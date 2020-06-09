from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from opaque_keys.edx.django.models import LearningContextKeyField

from openedx.core.djangoapps.config_model_utils.models import CourseAppConfigOptionsModel
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


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
    )
    config = JSONField(
        blank=False,
        default={},
        help_text=_("The discussion configuration data that can be user visible."),
    )


class LearningContextDiscussionConfig(models.Model):
    """
    Associates each learning context with a :class:`DiscussionConfiguration` via the config_key.
    """

    context_key = LearningContextKeyField(
        primary_key=True,
        db_index=True,
        unique=True,
        max_length=255,
        verbose_name=_("Learning Context"),
    )
    config_key = models.CharField(
        blank=False,
        max_length=100,
        verbose_name=_("Unique configuration identifier"),
        help_text=_("A unique identifier for this configuration."),
    )

    def clean(self):
        # Currently this only support courses, this can be extended whenever discussions
        # are available in other contexts
        if not CourseOverview.objects.filter(id=self.context_key).exists():
            raise ValidationError('Context Key should be an existing learning context.')
        if not DiscussionConfig.objects.filter(config_key=self.config_key).exists():
            raise ValidationError('Config Key should be an existing configuration object.')
