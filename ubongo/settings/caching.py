import os

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 20,
                "retry_on_timeout": True,
            },
        },
        "KEY_PREFIX": "ubongo",
        "TIMEOUT": 300,  
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache", 
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/2"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "sessions",
        "TIMEOUT": 86400,  # 24 hours
    },
    "wagtail_cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/3"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "wagtail",
        "TIMEOUT": 3600,  # 1 hour
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"
SESSION_COOKIE_AGE = 86400 * 7  # 1 week

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = "page"

WAGTAIL_CACHE = True
WAGTAIL_CACHE_BACKEND = "wagtail_cache"

DATABASE_POOL_SETTINGS = {
    "CONN_MAX_AGE": 3600,  # 1 hour
    "CONN_HEALTH_CHECKS": True,
}