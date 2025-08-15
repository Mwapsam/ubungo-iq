import os

import logging

logger = logging.getLogger(__name__)

try:
    from asgiref import local

    original_delattr = local._CVar.__delattr__

    def patched_delattr(self, name):
        try:
            return original_delattr(self, name)
        except AttributeError as e:
            if "object has no attribute 'value'" in str(e):
                logger.debug(f"Ignored asgiref AttributeError: {e}")
                return None
            raise

    local._CVar.__delattr__ = patched_delattr
except ImportError:
    pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

INSTALLED_APPS = [
    "blog",
    "home",
    "search",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_celery_beat",
    "django_extensions",
    "django_filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "ubongo.middleware.SecurityHeadersMiddleware",
    "ubongo.middleware.RateLimitMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "ubongo.middleware.ViewCountMiddleware",
]

ROOT_URLCONF = "ubongo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
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

WSGI_APPLICATION = "ubongo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

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

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

SITE_ID = 1

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000

WAGTAIL_SITE_NAME = "ubongo"

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

WAGTAILADMIN_BASE_URL = "https://ubongoiq.com"

WAGTAILIMAGES_JPEG_QUALITY = 85
WAGTAILIMAGES_WEBP_QUALITY = 80
WAGTAILIMAGES_AVIF_QUALITY = 70


WAGTAILIMAGES_EXTENSIONS = ["gif", "jpg", "jpeg", "png", "webp", "svg", "avif"]

WAGTAILIMAGES_FORMAT_CONVERSIONS = {
    "bmp": "avif",
    "png": "avif",
    "jpeg": "avif",
    "gif": "webp",
}

# Disable Wagtail image caching to prevent JSON serialization errors with Rendition objects
# This prevents "Object of type Rendition is not JSON serializable" errors in Redis
WAGTAILIMAGES_CACHE_BACKEND = "dummy"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

INSTALLED_APPS += ["django_celery_results"]

CELERY_TIMEZONE = TIME_ZONE

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
CONTENT_GENERATION_ENABLED = (
    os.environ.get("CONTENT_GENERATION_ENABLED", "True").lower() == "true"
)

AI_PROMPTS = {
    "article_outline": """Create an outline for: {topic}

1. Title
2. Intro
3. Main points (3 sections)
4. Conclusion""",
    "article_content": """Write a blog article based on this outline:

{outline}

Requirements:
- Professional tone
- 600-800 words
- Include examples
- Use markdown formatting
- Ready for publication""",
}
