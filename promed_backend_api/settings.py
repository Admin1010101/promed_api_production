from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

load_dotenv()
# ============================================================
# SENTRY CONFIGURATION
# ============================================================
sentry_sdk.init(
    dsn="https://e8b8032c2344202bda64fc938e4dc5db@o4509803038113792.ingest.us.sentry.io/4509803039031296",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

TESTING = True
# ============================================================
# BASE CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# Set DEBUG based on environment variable
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

# ============================================================
# AZURE PROXY/SECURITY CONFIGURATION
# ============================================================
RUNNING_ON_AZURE = os.getenv('WEBSITE_SITE_NAME') is not None

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False 

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# ============================================================
# CLIENT URL CONFIGURATION
# ============================================================
PRODUCTION_CLIENT_URL = os.getenv('CLIENT_BASE_URL', 'https://promedhealthplus.com')
LOCAL_CLIENT_URL = 'http://localhost:3000'

if DEBUG:
    BASE_CLIENT_URL = LOCAL_CLIENT_URL
else:
    BASE_CLIENT_URL = PRODUCTION_CLIENT_URL
# ============================================================
# ALLOWED HOSTS
# ============================================================
ALLOWED_HOSTS = [
     '127.0.0.1',
    'localhost',
    # Azure internal health check IPs
    '169.254.129.3',
    '169.254.129.5',
    '169.254.129.1',
    '169.254.129.2',
    '169.254.129.4',  # <--- CRITICAL FIX: Add the exact IP from the error
    '169.254.*',     # Wildcard for Azure internal IPs
    # Azure domains
    '.azurewebsites.net',
    '.azurefd.net',
    # Production domains
    'promedhealthplus.com',
    '.promedhealthplus.com',
]
# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    "https://*.azurewebsites.net",
    "https://*.azurefd.net",
    "https://promedhealthplus.com",
    "https://*.promedhealthplus.com",
]
# ============================================================
# INSTALLED APPS
# ============================================================
USER_APPS = [
    'provider_auth.apps.ProviderAuthConfig',
    'onboarding_ops.apps.OnboardingOpsConfig',
    'patients.apps.PatientsConfig',
    'sales_rep.apps.SalesRepConfig',
    'notes.apps.NotesConfig',
    'orders.apps.OrdersConfig',
    'order_items.apps.OrderItemsConfig',
    'cart.apps.CartConfig',
    'product.apps.ProductConfig',
    'notifications.apps.NotificationsConfig',
]

THIRD_PARTY_APPS = [
    'jazzmin',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
    'anymail',
    'drf_yasg',
    'storages',
    'phonenumber_field'
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + USER_APPS

# ============================================================
# CORS CONFIGURATION
# ============================================================
CORS_ALLOW_ALL_ORIGINS = True

# ============================================================
# MIDDLEWARE (NO WhiteNoise)
# ============================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# URL CONFIGURATION
# ============================================================
ROOT_URLCONF = 'promed_backend_api.urls'

# ============================================================
# TEMPLATES CONFIGURATION
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================
# WSGI CONFIGURATION
# ============================================================
WSGI_APPLICATION = 'promed_backend_api.wsgi.application'

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DB_NAME'),
        'USER': os.getenv('MYSQL_DB_USER'),
        'PASSWORD': os.getenv('MYSQL_DB_PASSWORD'),
        'HOST': os.getenv('MYSQL_DB_HOST'),
        'PORT': os.getenv('MYSQL_DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'ssl': {
                'ca': os.getenv('MYSQL_DB_SSL_CA_PATH')
            } if os.getenv('MYSQL_DB_SSL_CA_PATH') else {}
        }
    }
}

# ============================================================
# PASSWORD VALIDATION
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'core.validators.HIPAAPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]

# ============================================================
# INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ============================================================
# AUTH CONFIGURATION
# ============================================================
AUTH_USER_MODEL = 'provider_auth.User'
X_FRAME_OPTIONS = 'SAMEORIGIN'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# JWT CONFIGURATION
# ============================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=120),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=50),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ============================================================
# JAZZMIN ADMIN CONFIGURATION
# ============================================================
JAZZMIN_SETTINGS = {
    "site_title": "ProMed Health Plus Admin",
    "site_header": "ProMed Health Plus Portal",
    "site_brand": "ProMed Health Plus Portal",
    "welcome_sign": "Welcome to ProMed Health Plus Portal Admin",
    "copyright": "ProMed Health Plus Portal",
    "show_ui_builder": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": False,
    "brand_colour": "navbar-indigo",
    "accent": "accent-danger",
    "navbar": "navbar-indigo navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-indigo",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# ============================================================
# EMAIL CONFIGURATION (SendGrid)
# ============================================================
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'vastyle2010@gmail.com'

# ============================================================
# AZURE STORAGE GLOBAL CONFIGURATION (All settings for django-storages)
# ============================================================
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')

# CRITICAL: This base URL is used by AzureStorage backend for file links
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net' 
AZURE_URL_PROTOCOL = 'https' # Ensures links are HTTPS

# Set the container names for the storage backend to use
AZURE_STATIC_CONTAINER = 'static'
AZURE_MEDIA_CONTAINER = 'media'

# This setting forces the collectstatic command to overwrite existing files
# which is usually desired for CI/CD deployments.
AZURE_OVERWRITE_FILES = True


# ============================================================
# STATIC FILES CONFIGURATION 
# ============================================================
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATIC_URL must point to the base URL where files are served.
# Django-storages will append the full path, but the base URL must be correct.
STATIC_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_STATIC_CONTAINER}/'
# Points to the custom backend class
STATICFILES_STORAGE = 'promed_backend_api.storage_backends.AzureStaticStorage'
DEFAULT_FILE_STORAGE = 'promed_backend_api.storage_backends.AzureMediaStorage'
# ============================================================
# MEDIA FILES CONFIGURATION 
# ============================================================
# MEDIA_URL must point to the base URL where user-uploaded files are served.
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_MEDIA_CONTAINER}/'
# ============================================================
# STORAGES CONFIGURATION (Django 4.2+ using official backend)
# ============================================================
STORAGES = {
    # 'default' is for media files (user uploads)
    "default": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "account_name": AZURE_ACCOUNT_NAME,
            "account_key": AZURE_ACCOUNT_KEY,
            "azure_container": AZURE_MEDIA_CONTAINER,
            "overwrite_files": AZURE_OVERWRITE_FILES,
        },
    },
    # 'staticfiles' is for static files (CSS, JS, admin assets)
    "staticfiles": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "account_name": AZURE_ACCOUNT_NAME,
            "account_key": AZURE_ACCOUNT_KEY,
            "azure_container": AZURE_STATIC_CONTAINER,
            "overwrite_files": AZURE_OVERWRITE_FILES,
        },
    },
}

# ============================================================
# SESSION CONFIGURATION
# ============================================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ============================================================
# ADDITIONAL SETTINGS
# ============================================================
LOCAL_HOST = 'http://localhost:3000'