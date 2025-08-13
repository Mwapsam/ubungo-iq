import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'performance': {
            'format': 'PERF {asctime} {name} {message} duration={duration:.3f}s',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'debug.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['require_debug_true'],
        },
        'file_info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'application.log',
            'maxBytes': 1024 * 1024 * 25,  # 25MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 25,  # 25MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'security.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'file_performance': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'performance.log',
            'maxBytes': 1024 * 1024 * 20,  # 20MB
            'backupCount': 5,
            'formatter': 'performance',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'formatter': 'verbose',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file_info'],
    },
    'loggers': {
        'django': {
            'handlers': ['file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file_security'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ubongo': {
            'handlers': ['file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'blog': {
            'handlers': ['file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['file_performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'wagtail': {
            'handlers': ['file_info'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

LOGGING_CONFIG = None 
ADMINS = [
    ('Admin', os.getenv('ADMIN_EMAIL', 'admin@ubongoiq.com')),
]
MANAGERS = ADMINS

SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'noreply@ubongoiq.com')
DEFAULT_FROM_EMAIL = SERVER_EMAIL

LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', '30'))

PERFORMANCE_LOGGING_ENABLED = True
SLOW_REQUEST_THRESHOLD = float(os.getenv('SLOW_REQUEST_THRESHOLD', '1.0'))  # seconds