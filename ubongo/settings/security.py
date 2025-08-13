import os


SECURITY_SETTINGS = {
    'SECURE_SSL_REDIRECT': True,
    'SECURE_PROXY_SSL_HEADER': ('HTTP_X_FORWARDED_PROTO', 'https'),
    'SECURE_HSTS_SECONDS': 31536000,  # 1 year
    'SECURE_HSTS_INCLUDE_SUBDOMAINS': True,
    'SECURE_HSTS_PRELOAD': True,
    
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'CSRF_COOKIE_SECURE': True,
    'CSRF_COOKIE_HTTPONLY': True,
    'CSRF_COOKIE_SAMESITE': 'Lax',
    
    'X_FRAME_OPTIONS': 'DENY',
    
    'SECURE_CONTENT_TYPE_NOSNIFF': True,
    
    'SECURE_BROWSER_XSS_FILTER': True,
}

for setting, value in SECURITY_SETTINGS.items():
    globals()[setting] = value

CSRF_TRUSTED_ORIGINS = [
    'https://ubongoiq.com',
    'https://www.ubongoiq.com',
    'https://*.ubongoiq.com',
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email', 'first_name', 'last_name'),
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')  
WAGTAILADMIN_BASE_URL = os.getenv('WAGTAILADMIN_BASE_URL', 'https://ubongoiq.com')

SECURITY_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'ubongo.middleware.SecurityHeadersMiddleware',
    'ubongo.middleware.RateLimitMiddleware',
]

SECURITY_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join('logs', 'security.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'security',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'ubongo.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}