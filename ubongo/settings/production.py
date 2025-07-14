from .base import *

DEBUG = True

SECRET_KEY = os.getenv(
    "SECRET_KEY", "django-insecure-04p@%t4gven4uvy!eb)o2)e=e*k@7no3@7hae=a=ms0l3t)-2j"
)

ALLOWED_HOSTS = ["ubongo.dreamjobzm.com", "3.8.137.16", "127.0.0.1", "localhost"]

# Security
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

# Static + Media
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# Production database
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

# Email
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
