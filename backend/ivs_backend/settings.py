"""
iVote Systems (iVS) - Django Backend Settings
Secure, professional configuration for production-ready voting system
"""

from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import os

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production-immediately')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# CORS Configuration
# CORS settings
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000',
    cast=Csv()
)
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/.*\.app\.github\.dev$"]
# In dev/Codespaces allow all to avoid preflight blocks
CORS_ALLOW_ALL_ORIGINS = True if DEBUG else False
CORS_ALLOW_CREDENTIALS = True

# Application Definition
INSTALLED_APPS = [
    # Django apps
    'daphne',  # Must be first for Channels
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'channels',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'elections.apps.ElectionsConfig',
    'voting.apps.VotingConfig',
    'auditing.apps.AuditingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom security middleware
    'auditing.security_headers.SecurityHeadersMiddleware',
    'auditing.rate_limiting.RateLimitMiddleware',
    'auditing.session_management.SessionMiddleware',
]

ROOT_URLCONF = 'ivs_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ivs_backend.wsgi.application'
ASGI_APPLICATION = 'ivs_backend.asgi.application'

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(config('REDIS_HOST', default='127.0.0.1'), config('REDIS_PORT', default=6379, cast=int))],
        },
    },
}

# Database Configuration
# Use SQLite for development if DB_ENGINE is not set to PostgreSQL
DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': config('DB_NAME', default='ivs_voting_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'sslmode': config('DB_SSLMODE', default='disable'),
            }
        }
    }

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication & Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'JTI_CLAIM': 'jti',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if os.path.exists(BASE_DIR / 'static') else []

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default Primary Key Field Type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security Settings for Production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),
    'style-src': ("'self'", "'unsafe-inline'"),
    'img-src': ("'self'", 'data:', 'https:'),
}

if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
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
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'ivs_backend.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Encryption Settings
ENCRYPTION_KEY = config('ENCRYPTION_KEY', default='')  # Should be 32 bytes for AES-256

# Twilio Configuration for OTP/SMS
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# Email Configuration - Load from main .env file
try:
    from config.email_loader import get_email_settings
    _email_settings = get_email_settings()
    
    EMAIL_BACKEND = _email_settings['EMAIL_BACKEND']
    EMAIL_HOST = _email_settings['EMAIL_HOST']
    EMAIL_PORT = _email_settings['EMAIL_PORT']
    EMAIL_USE_TLS = _email_settings['EMAIL_USE_TLS']
    EMAIL_USE_SSL = _email_settings.get('EMAIL_USE_SSL', False)
    EMAIL_HOST_USER = _email_settings['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = _email_settings['EMAIL_HOST_PASSWORD']
    DEFAULT_FROM_EMAIL = _email_settings['DEFAULT_FROM_EMAIL']
    DEFAULT_FROM_NAME = _email_settings.get('DEFAULT_FROM_NAME', 'iVote Systems')
    SUPPORT_EMAIL = _email_settings['SUPPORT_EMAIL']
    ADMIN_EMAIL = _email_settings.get('ADMIN_EMAIL', 'admin@ivotesystems.com')
    EMAIL_TIMEOUT = _email_settings.get('EMAIL_TIMEOUT', 30)
    
    # Email Features
    EMAIL_NOTIFICATION_ENABLED = _email_settings['EMAIL_NOTIFICATION_ENABLED']
    EMAIL_VERIFICATION_REQUIRED = _email_settings.get('EMAIL_VERIFICATION_REQUIRED', True)
    EMAIL_VERIFICATION_DEADLINE_DAYS = _email_settings['EMAIL_VERIFICATION_DEADLINE_DAYS']
    EMAIL_REMINDER_DAYS_BEFORE = _email_settings['EMAIL_REMINDER_DAYS_BEFORE']
    
except ImportError:
    # Fallback to direct config reading
    EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = int(config('EMAIL_PORT', default='587'))
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default='True', cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default='False', cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@ivotesystems.com')
    DEFAULT_FROM_NAME = config('DEFAULT_FROM_NAME', default='iVote Systems')
    SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='support@ivotesystems.com')
    ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@ivotesystems.com')
    EMAIL_TIMEOUT = int(config('EMAIL_TIMEOUT', default='30'))
    EMAIL_NOTIFICATION_ENABLED = config('EMAIL_NOTIFICATION_ENABLED', default='True', cast=bool)
    EMAIL_VERIFICATION_REQUIRED = config('EMAIL_VERIFICATION_REQUIRED', default='True', cast=bool)
    EMAIL_VERIFICATION_DEADLINE_DAYS = int(config('EMAIL_VERIFICATION_DEADLINE_DAYS', default='14'))
    EMAIL_REMINDER_DAYS_BEFORE = int(config('EMAIL_REMINDER_DAYS_BEFORE', default='7'))

SITE_URL = config('SITE_URL', default='https://ivoting.example.com')

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('CACHE_LOCATION', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Rate Limiting
RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=True, cast=bool)
RATELIMIT_USE_CACHE = 'default'

# Vote Encryption Configuration
VOTE_ENCRYPTION_KEY = config(
    'VOTE_ENCRYPTION_KEY',
    default='development-encryption-key-change-in-production-32-bytes-minimum'
)

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'iVote Systems API',
    'DESCRIPTION': 'Secure, web-based online voting system API',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
}
