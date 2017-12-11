import uuid as uuid_tools
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models

from certificates.models import GeneratedCertificate  # pylint: disable=import-error
from model_utils.models import TimeStampedModel
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


class CourseEntitlementPolicy(models.Model):
    """
    Represents the Entitlement's policy for expiration, refunds, and regaining a used certificate
    """

    DEFAULT_EXPIRATION_PERIOD_DAYS = 450
    DEFAULT_REFUND_PERIOD_DAYS = 60
    DEFAULT_REGAIN_PERIOD_DAYS = 14

    # Use a DurationField to calculate time as it returns a timedelta, useful in performing operations with datetimes
    expiration_period = models.DurationField(
        default=timedelta(days=DEFAULT_EXPIRATION_PERIOD_DAYS),
        help_text="Duration in days from when an entitlement is created until when it is expired.",
        null=False
    )
    refund_period = models.DurationField(
        default=timedelta(days=DEFAULT_REFUND_PERIOD_DAYS),
        help_text="Duration in days from when an entitlement is created until when it is no longer refundable",
        null=False
    )
    regain_period = models.DurationField(
        default=timedelta(days=DEFAULT_REGAIN_PERIOD_DAYS),
        help_text=("Duration in days from when an entitlement is redeemed for a course run until "
                   "it is no longer able to be regained by a user."),
        null=False
    )
    site = models.ForeignKey(Site)

    def get_days_until_expiration(self, entitlement):
        """
        Returns an integer of number of days until the entitlement expires.
        Includes the logic for regaining an entitlement.
        """
        now = datetime.now(tz=pytz.UTC)
        expiry_date = entitlement.created + self.expiration_period
        days_until_expiry = (expiry_date - now).days
        if not entitlement.enrollment_course_run:
            return days_until_expiry
        course_overview = CourseOverview.get_from_id(entitlement.enrollment_course_run.course_id)
        # Compute the days left for the regain
        days_since_course_start = (now - course_overview.start).days
        days_since_enrollment = (now - entitlement.enrollment_course_run.created).days

        # We want to return whichever days value is less since it is then the more recent one
        days_until_regain_ends = (self.regain_period.days -  # pylint: disable=no-member
                                  min(days_since_course_start, days_since_enrollment))

        # If the base days until expiration is less than the days until the regain period ends, use that instead
        if days_until_expiry < days_until_regain_ends:
            return days_until_expiry

        return days_until_regain_ends  # pylint: disable=no-member

    def is_entitlement_regainable(self, entitlement):
        """
        Determines from the policy if an entitlement can still be regained by the user, if they choose
        to by leaving and regaining their entitlement within policy.regain_period days from start date of
        the course or their redemption, whichever comes later, and the expiration period hasn't passed yet
        """
        if entitlement.enrollment_course_run:
            if GeneratedCertificate.certificate_for_student(
                    entitlement.user_id, entitlement.enrollment_course_run.course_id) is not None:
                return False

            # This is >= because a days_until_expiration 0 means that the expiration day has not fully passed yet
            # and that the entitlement should not be expired as there is still time
            return self.get_days_until_expiration(entitlement) >= 0
        return False

    def is_entitlement_refundable(self, entitlement):
        """
        Determines from the policy if an entitlement can still be refunded, if the entitlement has not
        yet been redeemed (enrollment_course_run is NULL) and policy.refund_period has not yet passed, or if
        the entitlement has been redeemed, but the regain period hasn't passed yet.
        """
        # If there's no order number, it cannot be refunded
        if entitlement.order_number is None:
            return False

        # This is > because a get_days_since_created of refund_period means that that many days have passed,
        # which should then make the entitlement no longer refundable
        if entitlement.get_days_since_created() > self.refund_period.days:  # pylint: disable=no-member
            return False

        if entitlement.enrollment_course_run:
            return self.is_entitlement_regainable(entitlement)

        return True

    def is_entitlement_redeemable(self, entitlement):
        """
        Determines from the policy if an entitlement can be redeemed, if it has not passed the
        expiration period of policy.expiration_period, and has not already been redeemed
        """
        # This is < because a get_days_since_created of expiration_period means that that many days have passed,
        # which should then expire the entitlement
        return (entitlement.get_days_since_created() < self.expiration_period.days  # pylint: disable=no-member
                and not entitlement.enrollment_course_run)

    def __unicode__(self):
        return u'Course Entitlement Policy: expiration_period: {}, refund_period: {}, regain_period: {}'\
            .format(
                self.expiration_period,
                self.refund_period,
                self.regain_period,
            )


class CourseEntitlement(TimeStampedModel):
    """
    Represents a Student's Entitlement to a Course Run for a given Course.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    uuid = models.UUIDField(default=uuid_tools.uuid4, editable=False, unique=True)
    course_uuid = models.UUIDField(help_text='UUID for the Course, not the Course Run')
    expired_at = models.DateTimeField(
        null=True,
        help_text='The date that an entitlement expired, if NULL the entitlement has not expired.',
        blank=True
    )
    mode = models.CharField(max_length=100, help_text='The mode of the Course that will be applied on enroll.')
    enrollment_course_run = models.ForeignKey(
        'student.CourseEnrollment',
        null=True,
        help_text='The current Course enrollment for this entitlement. If NULL the Learner has not enrolled.',
        blank=True
    )
    order_number = models.CharField(max_length=128, null=True)
    _policy = models.ForeignKey(CourseEntitlementPolicy, null=True, blank=True)

    @property
    def expired_at_datetime(self):
        """
        Getter to be used instead of expired_at because of the conditional check and update
        """
        self.update_expired_at()
        return self.expired_at

    @expired_at_datetime.setter
    def expired_at_datetime(self, value):
        """
        Setter to be used instead for expired_at for consistency
        """
        self.expired_at = value

    @property
    def policy(self):
        """
        Getter to be used instead of _policy because of the null object pattern
        """
        return self._policy or CourseEntitlementPolicy()

    @policy.setter
    def policy(self, value):
        """
        Setter to be used instead of _policy because of the null object pattern
        """
        self._policy = value

    def get_days_since_created(self):
        """
        Returns an integer of number of days since the entitlement has been created
        """
        utc = pytz.UTC
        return (datetime.now(tz=utc) - self.created).days

    def update_expired_at(self):
        """
        Updates the expired_at attribute if it is not set AND it is expired according to the entitlement's policy,
        OR if the policy can no longer be regained AND the policy has been redeemed
        """
        if not self.expired_at:
            if (self.policy.get_days_until_expiration(self) < 0 or
                    (self.enrollment_course_run and not self.is_entitlement_regainable())):
                self.expired_at = datetime.utcnow()
                self.save()

    def get_days_until_expiration(self):
        """
        Returns an integer of number of days until the entitlement expires based on the entitlement's policy
        """
        return self.policy.get_days_until_expiration(self)

    def is_entitlement_regainable(self):
        """
        Returns a boolean as to whether or not the entitlement can be regained based on the entitlement's policy
        """
        return self.policy.is_entitlement_regainable(self)

    def is_entitlement_refundable(self):
        """
        Returns a boolean as to whether or not the entitlement can be refunded based on the entitlement's policy
        """
        return self.policy.is_entitlement_refundable(self)

    def is_entitlement_redeemable(self):
        """
        Returns a boolean as to whether or not the entitlement can be redeemed based on the entitlement's policy
        """
        return self.policy.is_entitlement_redeemable(self)

    @classmethod
    def set_enrollment(cls, entitlement, enrollment):
        """
        Fulfills an entitlement by specifying a session.
        """
        cls.objects.filter(id=entitlement.id).update(enrollment_course_run=enrollment)
