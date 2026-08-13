import re
import secrets

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

PHONE_REGEX = re.compile(r"^(?:\+?250|0)?7\d{8}$")

phone_validator = RegexValidator(
    regex=r"^0?7\d{8}$",
    message="Enter a valid phone number, e.g. 0783108892.",
)


def normalize_phone_number(raw: str) -> str:
    """Normalize an accepted Rwandan phone number to the canonical 07XXXXXXXX form."""
    value = (raw or "").strip().replace(" ", "").replace("-", "")
    if not PHONE_REGEX.match(value):
        raise ValidationError("Enter a valid phone number, e.g. 0783108892.")
    digits = value[-9:]
    return "0" + digits


def generate_referral_code() -> str:
    return secrets.token_hex(4).upper()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        phone_number = normalize_phone_number(phone_number)
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        max_length=15, unique=True, validators=[phone_validator]
    )
    full_name = models.CharField(max_length=120, blank=True)
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )
    is_fallback_referral = models.BooleanField(default=False)

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    welcome_bonus_paid = models.BooleanField(default=False)
    last_withdrawal_request_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.full_name or self.phone_number

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = generate_referral_code()
            while User.objects.filter(referral_code=code).exists():
                code = generate_referral_code()
            self.referral_code = code
        super().save(*args, **kwargs)

    def get_referral_path(self):
        from django.urls import reverse

        return f"{reverse('accounts:signup')}?ref={self.referral_code}"
