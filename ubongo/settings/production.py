from .base import *
from .caching import *

DEBUG = False

SECRET_KEY = os.getenv(
    "SECRET_KEY"
)

ALLOWED_HOSTS = [
    "*.ubongoiq.com",
    "ubongoiq.com",
    "3.8.137.16",
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
]

INSTALLED_APPS += [
    "storages",
]

SECURE_HSTS_SECONDS = 31536000
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True  
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760


STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

WAGTAILADMIN_STATIC_FILE_VERSION_STRINGS = False

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


STATICFILES_STORAGE = "ubongo.settings.storage_backends.StaticToS3Storage"

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "ubongo")

AWS_S3_ENDPOINT_URL = (
    "https://806f142a89e516c4e43c1cb14d6cc740.r2.cloudflarestorage.com"
)

AWS_S3_REGION_NAME = "auto"  
AWS_S3_SIGNATURE_VERSION = "s3v4"  
AWS_DEFAULT_ACL = "public-read"  
AWS_S3_CUSTOM_DOMAIN = "static.ubongoiq.com"  

STATICFILES_LOCATION = "static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATICFILES_LOCATION}/"
# STATIC_URL = AWS_S3_CUSTOM_DOMAIN 

MEDIAFILES_LOCATION = "media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "signature_version": AWS_S3_SIGNATURE_VERSION,
            "region_name": AWS_S3_REGION_NAME,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "signature_version": AWS_S3_SIGNATURE_VERSION,
            "region_name": AWS_S3_REGION_NAME,
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DATABASE_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DATABASE_NAME"),
        "USER": os.environ.get("DATABASE_USER"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD"),
        "HOST": os.environ.get("DATABASE_HOST"),
        "PORT": os.environ.get("DATABASE_PORT"),
        "CONN_MAX_AGE": 600,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "live.smtp.mailtrap.io")
EMAIL_PORT = os.environ.get("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "api")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "api")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "noreply@yourdomain.com"

INTERNAL_IPS = [
    "127.0.0.1",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "utils/logging.log",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
}

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

CACHES["default"]["LOCATION"] = REDIS_URL + "/0"
CACHES["sessions"]["LOCATION"] = REDIS_URL + "/1"
CACHES["wagtail_cache"]["LOCATION"] = REDIS_URL + "/2"
CACHES["wagtail_images"]["LOCATION"] = REDIS_URL + "/4"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://dp7dk6iy0oxso.cloudfront.net"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://dp7dk6iy0oxso.cloudfront.net"]
CSP_FONT_SRC = ["'self'", "https://fonts.gstatic.com", "https://dp7dk6iy0oxso.cloudfront.net"]
CSP_IMG_SRC = ["'self'", "data:", "https:", "https://dp7dk6iy0oxso.cloudfront.net"]
CSP_CONNECT_SRC = ["'self'"]
CSP_FRAME_SRC = ["'none'"]
CSP_OBJECT_SRC = ["'none'"]

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "sessions"

MONITORING_SETTINGS = {
    "SENTRY_DSN": os.getenv("SENTRY_DSN"),
    "NEW_RELIC_LICENSE_KEY": os.getenv("NEW_RELIC_LICENSE_KEY"),
    "DATADOG_API_KEY": os.getenv("DATADOG_API_KEY"),
}

if MONITORING_SETTINGS["SENTRY_DSN"]:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=MONITORING_SETTINGS["SENTRY_DSN"],
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=False,
                signals_spans=False,
            ),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=ENVIRONMENT,
        release=os.getenv("APP_VERSION", "unknown"),
    )
