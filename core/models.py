from django.conf import settings
from django.db import models


class SiteSettings(models.Model):
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="International format without '+', e.g. 250783108892 (used for the WhatsApp chat link).",
    )
    whatsapp_group_url = models.URLField(blank=True)
    telegram_group_url = models.URLField(blank=True)
    payee_name = models.CharField(max_length=120, blank=True)
    payment_code = models.CharField(max_length=60, blank=True)
    fallback_referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"is_staff": True},
        help_text="Users who sign up without a referral code are attributed to this admin.",
    )
    min_withdrawal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
