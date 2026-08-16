"""
Django settings for valley_investment project.
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-$wv_fz^w#6ej@qfhe-v@mh8u@gaem^j!8#)duskq)!5f-=gef_",
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Railway assigns the public domain at deploy time, so it can't be baked into
# ALLOWED_HOSTS by hand - pick it up from the environment it injects.
for _railway_var in ("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_PRIVATE_DOMAIN"):
    _railway_domain = os.environ.get(_railway_var, "").strip()
    if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_railway_domain)
        if _railway_var == "RAILWAY_PUBLIC_DOMAIN":
            _railway_origin = f"https://{_railway_domain}"
            if _railway_origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(_railway_origin)

# Railway's healthcheck hits the container with its own Host header.
if os.environ.get("RAILWAY_ENVIRONMENT_NAME") and "healthcheck.railway.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("healthcheck.railway.app")

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

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Valley Investment business constants ---
WELCOME_BONUS_AMOUNT = Decimal("1000")
REFERRAL_COMMISSION_RATE = Decimal("0.08")
WITHDRAWAL_COOLDOWN_HOURS = 24
WITHDRAWAL_OPEN_TIME = "06:30"
WITHDRAWAL_CLOSE_TIME = "23:30"
MAX_SCREENSHOT_SIZE_MB = 5
