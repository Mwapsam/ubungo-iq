from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-3*@3uzvxkw+c#)8nd$so6%-jdzm8c6c8lq-2uiib=6n=d8$p)9"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Development static files - no caching
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Force template reloading in development
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG
TEMPLATES[0]['OPTIONS']['auto_reload'] = True

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_CACHE_BACKEND = "default"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DATABASE_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DATABASE_NAME", "ubongo_iq_user"),
        "USER": os.environ.get("DATABASE_USER", "ubongo_iq_user"),
        "PASSWORD": os.environ.get(
            "DATABASE_PASSWORD",
            "SuguASDJGHASFHGVXNZHJK78367834278adsg@#yugfeaugdsfghdfsfhgxdSAAFSGHVDghusdvd#@ugb",
        ),
        "HOST": os.environ.get("DATABASE_HOST", "db"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}
