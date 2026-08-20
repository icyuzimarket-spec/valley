"""
Django settings for valley_investment project.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# Set by Railway in both the build and the deploy, so it's the marker for
# "this is a real deployment, not someone's laptop".
ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))

# A deployment must never fall back to the key committed in this file: anyone
# reading the repo could forge session cookies and password-reset tokens.
DEBUG = os.environ.get("DEBUG", "False" if ON_RAILWAY else "True") == "True"

if DEBUG:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "django-insecure-$wv_fz^w#6ej@qfhe-v@mh8u@gaem^j!8#)duskq)!5f-=gef_",
    )
else:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    if not SECRET_KEY:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set when DEBUG is False. Generate one with:\n"
            "  python -c \"from django.core.management.utils import get_random_secret_key;"
            " print(get_random_secret_key())\"\n"
            "then set it as a SECRET_KEY environment variable on the service."
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

if ON_RAILWAY:
    # Railway generates the public domain (e.g. valley-production-3535.up.railway.app)
    # after the service is created, and does *not* inject it as RAILWAY_PUBLIC_DOMAIN,
    # so there is no variable to read it from - match the whole domain space instead.
    # Only Railway's own proxy can route to this container, so a wildcard here does
    # not let anyone else's app reach it.
    for _host in (".up.railway.app", "healthcheck.railway.app"):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)
    if "https://*.up.railway.app" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append("https://*.up.railway.app")

    # Only the private domain is published as a variable; it's how other
    # services in the project reach this one.
    _private_domain = os.environ.get("RAILWAY_PRIVATE_DOMAIN", "").strip()
    if _private_domain and _private_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_private_domain)

# Hardening that only makes sense once we're not on the local dev server.
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"


# ---------------------------------------------------------------------------
# Maintenance mode
#
# While this is True the site serves nothing but the maintenance page - every
# page, every visitor, staff and the Django admin included. There is no switch
# in the admin and no environment variable on purpose: the only way back is to
# set this to False, commit, and deploy.
# ---------------------------------------------------------------------------
MAINTENANCE_MODE = True

# The test suite exercises the real site; with the maintenance page in front of
# every URL it would just get a 503 back from all of them. The tests that are
# about maintenance mode switch it on themselves with override_settings.
if "test" in sys.argv:
    MAINTENANCE_MODE = False

MAINTENANCE_MESSAGE = (
    "The display system has a technical problem. Our team is fixing it - please wait."
)

# wa.me needs the international format: no '+', no leading 0.
# 0795 927 291 in Rwanda (+250) is 250795927291.
MAINTENANCE_WHATSAPP = "250795927291"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "accounts",
    "core",
    "investments",
    "wallet",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves the collectstatic'd snapshot in STATIC_ROOT, which
    # would shadow live edits during development. Only needed once DEBUG is
    # off - runserver's own staticfiles handling covers local dev.
    *([] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]),
    # Ahead of session and auth: a blocked request needs neither, and this
    # way maintenance mode cannot be bypassed by anything downstream.
    "core.middleware.MaintenanceModeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "valley_investment.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "valley_investment.wsgi.application"


# Hosts with an ephemeral filesystem (Railway et al.) wipe the container's disk
# on every deploy, so a SQLite file there loses every user and investment. When
# a managed database is attached, DATABASE_URL points at it; fall back to SQLite
# for local development.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard_redirect"
LOGOUT_REDIRECT_URL = "core:home"

LANGUAGE_CODE = "en-us"

# Rwanda has no DST; all "daily"/business-hour logic depends on this being correct.
TIME_ZONE = "Africa/Kigali"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    # Manifest storage needs `collectstatic` to have run (it looks up hashed
    # filenames from a manifest), which would break `runserver` in a fresh
    # dev checkout. Only use it once DEBUG is off (i.e. production).
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Payment proof storage (Cloudflare R2) ---
# Payment screenshots are the only user uploads, and they are the evidence
# behind every approved investment. On a host with an ephemeral disk they would
# be lost on each redeploy, so keep them in R2 whenever it is configured. With
# no R2 credentials the app falls back to local disk, which is what local
# development and the test suite use.
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "").strip()
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "").strip()
R2_REGION = os.environ.get("R2_REGION", "auto").strip() or "auto"

# R2's S3 endpoint is derivable from the account ID, so accept either.
R2_ENDPOINT = os.environ.get("R2_ENDPOINT", "").strip()
if not R2_ENDPOINT and R2_ACCOUNT_ID:
    R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Cloudflare's bucket page shows the S3 API address with the bucket appended
# ("https://<account>.r2.cloudflarestorage.com/<bucket>"), which is the value
# people copy into R2_ENDPOINT. boto3 wants the host on its own and appends the
# bucket itself, so leaving the path on turns every request into
# /<bucket>/<bucket>/<key> and nothing can be stored or fetched. An S3 endpoint
# never legitimately carries a path, so drop it.
if R2_ENDPOINT:
    _r2_parts = urlsplit(R2_ENDPOINT if "//" in R2_ENDPOINT else f"https://{R2_ENDPOINT}")
    R2_ENDPOINT = urlunsplit((_r2_parts.scheme or "https", _r2_parts.netloc, "", "", ""))

_R2_SETTINGS = {
    "R2_BUCKET_NAME": R2_BUCKET_NAME,
    "R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
    "R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
    "R2_ENDPOINT (or R2_ACCOUNT_ID)": R2_ENDPOINT,
}
R2_MISSING_SETTINGS = sorted(name for name, value in _R2_SETTINGS.items() if not value)
USE_R2 = not R2_MISSING_SETTINGS

# A half-configured bucket is always a mistake: uploads would silently land on
# the local disk, which every managed host wipes on redeploy, and the proof
# behind an approved investment would be gone. Fail loudly instead of storing
# payment evidence somewhere it cannot survive.
if R2_MISSING_SETTINGS and len(R2_MISSING_SETTINGS) < len(_R2_SETTINGS):
    raise ImproperlyConfigured(
        "Cloudflare R2 is partially configured. Missing: "
        + ", ".join(R2_MISSING_SETTINGS)
        + ". Set all of them, or none to store uploads on the local disk."
    )

if USE_R2:
    from botocore.config import Config as _BotoConfig

    # boto3 1.36+ defaults to `when_supported`, which sends every upload as a
    # chunked body with a trailing CRC32 checksum (Content-Encoding:
    # aws-chunked, X-Amz-Content-SHA256: STREAMING-UNSIGNED-PAYLOAD-TRAILER).
    # R2 does not implement that trailer flow, so each screenshot upload is
    # rejected. `when_required` sends a plain body, which R2 accepts.
    #
    # django-storages only builds its own botocore Config when none is passed,
    # so the addressing style and signature version have to be repeated here.
    _R2_CLIENT_CONFIG = _BotoConfig(
        # R2 only serves the path-style endpoint, and only signs v4.
        s3={"addressing_style": "path"},
        signature_version="s3v4",
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "endpoint_url": R2_ENDPOINT,
            "region_name": R2_REGION,
            "client_config": _R2_CLIENT_CONFIG,
            # R2 has no ACL support; sending one makes every upload fail.
            "default_acl": None,
            "object_parameters": {"CacheControl": "private, max-age=3600"},
            # Payment proofs identify people and amounts, so the bucket stays
            # private and every URL is a short-lived signed one.
            "querystring_auth": True,
            "querystring_expire": 3600,
            # Never let one upload silently overwrite another's proof.
            "file_overwrite": False,
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Valley Investment business constants ---
WELCOME_BONUS_AMOUNT = Decimal("1000")
REFERRAL_COMMISSION_RATE = Decimal("0.08")
WITHDRAWAL_COOLDOWN_HOURS = 24
WITHDRAWAL_OPEN_TIME = "06:30"
WITHDRAWAL_CLOSE_TIME = "23:30"
MAX_SCREENSHOT_SIZE_MB = 5
