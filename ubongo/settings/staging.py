from .base import *
from .security import *
from .caching import *
from .logging import *

DEBUG = False

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in staging")

ALLOWED_HOSTS = [
    "staging.ubongoiq.com",
    "*.staging.ubongoiq.com",
    "127.0.0.1",
    "localhost",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("STAGING_DATABASE_NAME", "ubongo_staging"),
        "USER": os.getenv("STAGING_DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("STAGING_DATABASE_PASSWORD"),
        "HOST": os.getenv("STAGING_DATABASE_HOST", "localhost"),
        "PORT": os.getenv("STAGING_DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 300,  # 5 minutes
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": "prefer",
        }
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("STAGING_EMAIL_HOST", "smtp.mailtrap.io")
EMAIL_PORT = int(os.getenv("STAGING_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("STAGING_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("STAGING_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "staging@ubongoiq.com"
SERVER_EMAIL = "staging@ubongoiq.com"

AWS_ACCESS_KEY_ID = os.getenv("STAGING_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("STAGING_AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("STAGING_AWS_STORAGE_BUCKET_NAME", "ubongo-staging")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400, public",  # 1 day cache
}

AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

STATICFILES_LOCATION = "static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATICFILES_LOCATION}/"

MEDIAFILES_LOCATION = "media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"

STORAGES = {
    "default": {"BACKEND": "ubongo.settings.storage_backends.mediaRootS3Boto3Storage"},
    "staticfiles": {"BACKEND": "ubongo.settings.storage_backends.StaticToS3Storage"},
}

REDIS_URL = os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/1")

CACHES["default"]["LOCATION"] = REDIS_URL
CACHES["sessions"]["LOCATION"] = os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/2")
CACHES["wagtail_cache"]["LOCATION"] = os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/3")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 3600  
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = [
    "https://staging.ubongoiq.com",
    "https://*.staging.ubongoiq.com",
]

WAGTAILADMIN_BASE_URL = "https://staging.ubongoiq.com"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "ubongo.middleware.SecurityHeadersMiddleware",
    "ubongo.middleware.RateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "ubongo.middleware.ViewCountMiddleware",
]

LOGGING["loggers"].update({
    "django.db.backends": {
        "handlers": ["file_debug"],
        "level": "INFO",  
        "propagate": False,
    },
    "ubongo.performance": {
        "handlers": ["file_performance"],
        "level": "DEBUG",
        "propagate": False,
    }
})

INSTALLED_APPS += [
    "django_extensions",  
]

PERFORMANCE_LOGGING_ENABLED = True
SLOW_REQUEST_THRESHOLD = 0.5  

ADMINS = [
    ("Staging Admin", os.getenv("STAGING_ADMIN_EMAIL", "staging-admin@ubongoiq.com")),
]

ENVIRONMENT = "staging"

FEATURE_FLAGS = {
    "ENABLE_ANALYTICS": True,
    "ENABLE_CACHING": True,
    "ENABLE_RATE_LIMITING": True,
    "ENABLE_IMAGE_OPTIMIZATION": True,
    "ENABLE_SEO_FEATURES": True,
}

TEST_RUNNER = "django.test.runner.DiscoverRunner"