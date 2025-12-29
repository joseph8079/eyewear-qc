from pathlib import Path
import os
import dj_database_url

# -------------------------------------------------
# BASE
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "unsafe-dev-secret-key-change-me"
)

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "*"
).split(",")

# -------------------------------------------------
# APPLICATIONS
# -------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "qc",
]

# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -------------------------------------------------
# URLS / WSGI
# -------------------------------------------------
ROOT_URLCONF = "eyewear_qc.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "eyewear_qc.wsgi.application"

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        ),
        conn_max_age=600,
        ssl_require=False,
    )
}

# -------------------------------------------------
# AUTH
# -------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True

# -------------------------------------------------
# STATIC / MEDIA
# -------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------
# QC CONFIG (OPTIONAL, SAFE DEFAULTS)
# -------------------------------------------------
QC_FLAG_LOOKBACK_DAYS = int(os.environ.get("QC_FLAG_LOOKBACK_DAYS", 7))
QC_FLAG_MIN_SAMPLE = int(os.environ.get("QC_FLAG_MIN_SAMPLE", 20))
QC_FLAG_DEFECT_RATE_THRESHOLD = float(
    os.environ.get("QC_FLAG_DEFECT_RATE_THRESHOLD", 0.12)
)

QC_SLA_URGENT_HOURS = int(os.environ.get("QC_SLA_URGENT_HOURS", 4))
QC_SLA_STAGE_MAX_HOURS = int(os.environ.get("QC_SLA_STAGE_MAX_HOURS", 2))

QC_TRAINING_INSPECTIONS = int(
    os.environ.get("QC_TRAINING_INSPECTIONS", 30)
)
