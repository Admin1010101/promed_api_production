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
    dsn=os.getenv("SENTRY_DSN", "https://e8b8032c2344202bda64fc938e4dc5db@o4509803038113792.ingest.us.sentry.io/4509803039031296"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0, 
    send_default_pii=True
)

TESTING = False

APPEND_SLASH = True# Changed to False for production consistency

# ============================================================
# BASE CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

# ============================================================
# AZURE PROXY/SECURITY CONFIGURATION
# ============================================================
RUNNING_ON_AZURE = os.getenv('WEBSITE_SITE_NAME') is not None
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG 
CSRF_COOKIE_SECURE = not DEBUG
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
    '169.254.129.*',
    '.azurewebsites.net',
    '.azurefd.net',
    'promedhealthplus.com',
    '.promedhealthplus.com',
    '*', 
]
if os.getenv('WEBSITE_HOSTNAME'):
    ALLOWED_HOSTS.append(os.getenv('WEBSITE_HOSTNAME'))

# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    "https://*.azurewebsites.net",
    "https://*.azurefd.net",
    "https://promedhealthplus.com",
    "https://*.promedhealthplus.com",
    "http://localhost:3000"
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
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
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
# PASSWORD VALIDATION, INTERNATIONALIZATION, REST FRAMEWORK, AUTH, JWT, JAZZMIN, EMAIL (omitted for brevity)
# ... [Remaining settings blocks: AUTH_PASSWORD_VALIDATORS, LANGUAGE_CODE, REST_FRAMEWORK, AUTH_USER_MODEL, SIMPLE_JWT, JAZZMIN_SETTINGS, JAZZMIN_UI_TWEAKS, EMAIL CONFIGURATION]
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
# AZURE STORAGE GLOBAL CONFIGURATION
# ============================================================
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')

# Azure Front Door endpoint (CDN)
AZURE_FRONTDOOR_ENDPOINT = 'promedhealth-frontdoor-h4c4bkcxfkduezec.z02.azurefd.net'

# CRITICAL FIX: TEMPORARILY REVERT TO DIRECT BLOB STORAGE DOMAIN.
# This bypasses the CDN issue that causes the InvalidQueryParameterValue error.
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net' 

AZURE_STATIC_CONTAINER = 'static'
AZURE_MEDIA_CONTAINER = 'media'
AZURE_OVERWRITE_FILES = True


# ============================================================
# STATIC AND MEDIA FILES CONFIGURATION (CONDITIONAL FIX)
# ============================================================
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
STATICFILES_DIRS = []
PROJECT_STATIC_DIR = os.path.join(BASE_DIR, 'static')
if os.path.isdir(PROJECT_STATIC_DIR):
    STATICFILES_DIRS.append(PROJECT_STATIC_DIR)


if DEBUG:
    # --- DEVELOPMENT SETTINGS (Local File System) ---
    STATIC_URL = '/static/' # Use simple path for local dev
    MEDIA_URL = '/media/'
    
    # Use Django's default storage backends
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    
else:
    # --- PRODUCTION SETTINGS (Azure Blob Storage + CDN) ---
    
    # CRITICAL FIX (Kept): Set only the container path.
    STATIC_URL = f'/{AZURE_STATIC_CONTAINER}/'
    MEDIA_URL = f'/{AZURE_MEDIA_CONTAINER}/'

    # FIX: Use custom storage backends to avoid URL generation conflicts
    STORAGES = {
        "default": {
            "BACKEND": "promed_backend_api.storage_backends.AzureMediaStorage",
            "OPTIONS": {}, # Options are defined in the custom class
        },
        "staticfiles": {
            "BACKEND": "promed_backend_api.storage_backends.AzureStaticStorage",
            "OPTIONS": {
                # Only include non-inherited options here
                "cache_control": "max-age=31536000, public, immutable",
            },
        },
    }

# ============================================================
# SESSION CONFIGURATION
# ============================================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ============================================================
# ADDITIONAL SETTINGS (End of file)
# =================================