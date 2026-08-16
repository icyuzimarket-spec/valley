"""Create the admin account from environment variables.

Hosts like Railway have no convenient interactive shell, so the
`create_admin` management command is awkward to run there. This migration does
the same job during the deploy's `migrate` step instead.

It is a no-op unless both ADMIN_PHONE and ADMIN_PASSWORD are set, so local
checkouts and the test suite are unaffected. The password is only ever read
from the environment - never store one in this file, which is public.
"""

import os
import re
import secrets

from django.contrib.auth.hashers import make_password
from django.db import migrations

# Mirrors accounts.models.PHONE_REGEX. Duplicated rather than imported so this
# migration keeps working if the model's validation changes later.
PHONE_REGEX = re.compile(r"^(?:\+?250|0)?7\d{8}$")


def normalize_phone_number(raw):
    value = (raw or "").strip().replace(" ", "").replace("-", "")
    if not PHONE_REGEX.match(value):
        return None
    return "0" + value[-9:]


def create_admin(apps, schema_editor):
    phone_number = os.environ.get("ADMIN_PHONE", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not phone_number or not password:
        return

    phone_number = normalize_phone_number(phone_number)
    if phone_number is None:
        # Don't fail the deploy over a typo in a variable - the account can
        # still be created with the create_admin command.
        print("  ADMIN_PHONE is not a valid phone number; skipping admin creation.")
        return

    User = apps.get_model("accounts", "User")
    if User.objects.filter(phone_number=phone_number).exists():
        return

    # The historical model has no custom save(), so the referral code that
    # User.save() would normally generate has to be built here.
    referral_code = secrets.token_hex(4).upper()
    while User.objects.filter(referral_code=referral_code).exists():
        referral_code = secrets.token_hex(4).upper()

    admin = User.objects.create(
        phone_number=phone_number,
        password=make_password(password),
        full_name=os.environ.get("ADMIN_FULL_NAME", "Valley Admin"),
        referral_code=referral_code,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )

    SiteSettings = apps.get_model("core", "SiteSettings")
    site_settings, _ = SiteSettings.objects.get_or_create(pk=1)
    if not site_settings.fallback_referrer:
        site_settings.fallback_referrer = admin
        site_settings.save()


def noop(apps, schema_editor):
    """Deliberately does not delete the admin - unapplying a migration should
    not destroy an account that may own referrals and approvals by now."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("core", "0002_alter_sitesettings_whatsapp_number"),
    ]

    operations = [
        migrations.RunPython(create_admin, noop),
    ]
