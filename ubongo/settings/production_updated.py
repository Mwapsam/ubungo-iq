from .base import *
from .security import *
from .caching import *
from .logging import *

DEBUG = False

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in production")

ALLOWED_HOSTS = [
    "ubongoiq.com",
    "www.ubongoiq.com", 
    "*.ubongoiq.com",
    os.getenv("LOAD_BALANCER_IP", ""),
].strip()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USER"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 3600, 
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 10,
            "options": "-c default_transaction_isolation=read_committed"
        }
    }
}

if os.getenv("DATABASE_READ_HOST"):
    DATABASES["read"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_READ_USER", os.getenv("DATABASE_USER")),
        "PASSWORD": os.getenv("DATABASE_READ_PASSWORD", os.getenv("DATABASE_PASSWORD")),
        "HOST": os.getenv("DATABASE_READ_HOST"),
        "PORT": os.getenv("DATABASE_READ_PORT", "5432"),
        "CONN_MAX_AGE": 3600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": "require",
        }
    }
    
    DATABASE_ROUTERS = ["ubongo.routers.DatabaseRouter"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.amazonaws.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = 30

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@ubongoiq.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "server@ubongoiq.com")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

AWS_CLOUDFRONT_DOMAIN = os.getenv("AWS_CLOUDFRONT_DOMAIN")
CLOUDFRONT_ID = os.getenv("AWS_CLOUDFRONT_ID")

AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=31536000, public",  
}

AWS_S3_CUSTOM_DOMAIN = (
    AWS_CLOUDFRONT_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
)

STATICFILES_LOCATION = "static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATICFILES_LOCATION}/"

MEDIAFILES_LOCATION = "media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"

STORAGES = {
    "default": {"BACKEND": "ubongo.settings.storage_backends.mediaRootS3Boto3Storage"},
    "staticfiles": {"BACKEND": "ubongo.settings.storage_backends.StaticToS3Storage"},
}

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

CACHES["default"]["LOCATION"] = REDIS_URL
CACHES["sessions"]["LOCATION"] = os.getenv("REDIS_URL", "redis://redis:6379/1") 
CACHES["wagtail_cache"]["LOCATION"] = os.getenv("REDIS_URL", "redis://redis:6379/2")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TASK_COMPRESSION = "gzip"
CELERY_RESULT_COMPRESSION = "gzip"

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000 
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 86400 * 7  

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = [
    "https://ubongoiq.com",
    "https://www.ubongoiq.com",
    "https://*.ubongoiq.com",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024  
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024  
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

WAGTAILADMIN_BASE_URL = "https://ubongoiq.com"

ADMIN_URL = os.getenv("ADMIN_URL", "secure-admin/")

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

INSTALLED_APPS += [
    "storages",
    "django_celery_results",
    "django_celery_beat",
]

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ["django_extensions"]]

LOGGING["handlers"]["mail_admins"]["level"] = "ERROR"
LOGGING["handlers"]["file_error"]["level"] = "WARNING"

LOGGING["loggers"].update({
    "django.security.DisallowedHost": {
        "handlers": ["file_security", "mail_admins"],
        "level": "WARNING",
        "propagate": False,
    },
    "django.request": {
        "handlers": ["file_error", "mail_admins"],
        "level": "ERROR",
        "propagate": False,
    }
})

PERFORMANCE_LOGGING_ENABLED = True
SLOW_REQUEST_THRESHOLD = 2.0  

ADMINS = [
    ("Production Admin", os.getenv("ADMIN_EMAIL", "admin@ubongoiq.com")),
    ("DevOps Team", os.getenv("DEVOPS_EMAIL", "devops@ubongoiq.com")),
]
MANAGERS = ADMINS

HEALTH_CHECK_ENDPOINTS = {
    "database": "/health/db/",
    "cache": "/health/cache/", 
    "storage": "/health/storage/",
}

FEATURE_FLAGS = {
    "ENABLE_ANALYTICS": True,
    "ENABLE_CACHING": True,
    "ENABLE_RATE_LIMITING": True,
    "ENABLE_IMAGE_OPTIMIZATION": True,
    "ENABLE_SEO_FEATURES": True,
    "ENABLE_COMPRESSION": True,
}

ENVIRONMENT = "production"

CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
CSP_FONT_SRC = ["'self'", "https://fonts.gstatic.com"]
CSP_IMG_SRC = ["'self'", "data:", "https:"]
CSP_CONNECT_SRC = ["'self'"]
CSP_FRAME_SRC = ["'none'"]
CSP_OBJECT_SRC = ["'none'"]

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "sessions"

if os.getenv("ELASTICSEARCH_URL"):
    WAGTAILSEARCH_BACKENDS = {
        "default": {
            "BACKEND": "wagtail.search.backends.elasticsearch7",
            "URLS": [os.getenv("ELASTICSEARCH_URL")],
            "INDEX": "ubongo",
            "OPTIONS": {
                "ca_certs": os.getenv("ELASTICSEARCH_CA_PATH"),
                "verify_certs": True,
            },
        }
    }

BACKUP_SETTINGS = {
    "DATABASE_BACKUP_ENABLED": True,
    "MEDIA_BACKUP_ENABLED": True,
    "BACKUP_RETENTION_DAYS": 30,
    "BACKUP_S3_BUCKET": os.getenv("BACKUP_S3_BUCKET"),
}

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