import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "asiko-django-dev-key-2026-insecure-change-in-prod")

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "apps.boutique_core",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "boutique"),
        "USER": os.getenv("POSTGRES_USER", "Asiko"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "npg_IxpdXZ5yr9va"),
        "HOST": os.getenv("POSTGRES_HOST", "ep-lucky-dew-a7vwotgb-pooler.ap-southeast-2.aws.neon.tech"),
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
