# settings.py
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
import dj_database_url

load_dotenv()

sentry_sdk.init(
    dsn="https://e8b8032c2344202bda64fc938e4dc5db@o4509803038113792.ingest.us.sentry.io/4509803039031296",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

# --- AZURE PROXY/SECURITY CONFIGURATION ---
# Detect if running on Azure
RUNNING_ON_AZURE = os.getenv('WEBSITE_SITE_NAME') is not None

# For Django to trust the headers passed by the Azure Load Balancer/Proxy
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# This tells Django to trust the X-Forwarded-Proto header for 'https'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CRITICAL FIX: SECURE_SSL_REDIRECT must be False on Azure App Service
# Azure handles the HTTPS redirection at the load balancer. Setting this to True
# causes a redirect loop and a 403 error.
SECURE_SSL_REDIRECT = False 

# Secure cookies - these are safe to keep enabled
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# --- END AZURE PROXY/SECURITY CONFIGURATION ---

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# Set DEBUG based on environment variable
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

# ALLOWED_HOSTS - Covers all Azure deployment scenarios
ALLOWED_HOSTS = [
    # Local Development
    '127.0.0.1',
    'localhost',
    # Azure internal health probe IP (Required for startup checks)
    '169.254.129.3',
    # Wildcard covers all Azure subdomains including temporary deployment URLs
    '.azurewebsites.net',
    # Other deployment platforms
    '.onrender.com',
    'pythonanywhere.com',
    'wchandler2025.pythonanywhere.com',
]

# CSRF_TRUSTED_ORIGINS - Allow HTTPS from Azure domains
CSRF_TRUSTED_ORIGINS = [
    "https://promedhealthplus-portal-api-1.onrender.com",
    "https://app-promed-backend-prod-dev.azurewebsites.net",
    "https://*.azurewebsites.net",
    # Add your React frontend domain here when deployed
    # "https://your-frontend-domain.com",
]

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

# CORS Configuration - Allow all origins for now
# Consider restricting this to specific domains in production (HIPAA best practice)
CORS_ALLOW_ALL_ORIGINS = True

# --- CRITICAL FIX: Middleware Ordering ---
# CorsMiddleware and SecurityMiddleware should be first. 
# Whitenoise is usually last after SessionMiddleware.
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # 1st - Must come before other middlewares that might use the CORS headers
    'django.middleware.security.SecurityMiddleware', # 2nd - Needs to run early
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Last, or near last
]
# --- END CRITICAL FIX ---

ROOT_URLCONF = 'promed_backend_api.urls'

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

WSGI_APPLICATION = 'promed_backend_api.wsgi.application'

# Database Configuration
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
            # SSL Configuration for Azure MySQL
            # FIX: Use simple truthiness check for SSL options key existence
            'ssl': {
                'ca': os.getenv('MYSQL_DB_SSL_CA_PATH')
            } if os.getenv('MYSQL_DB_SSL_CA_PATH') else {}
        }
    }
}

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', # Needed for Django Admin
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

AUTH_USER_MODEL = 'provider_auth.User'

# X-Frame-Options set to SAMEORIGIN is a good balance for the Admin interface
X_FRAME_OPTIONS = 'SAMEORIGIN'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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

JAZZMIN_SETTINGS = {
    "site_title": "LMS Admin",
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

# Email Configuration
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'vastyle2010@gmail.com'

# Azure Storage Configuration
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')
AZURE_CONTAINER = 'media'

LOCAL_HOST = 'http://localhost:3000'

# Static files root directory
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "promed_backend_api.storage_backends.AzureMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "promed_backend_api.storage_backends.AzureStaticStorage",
    },
}

# Azure URLs
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
STATIC_URL = f'https://{AZURE_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/media/'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'