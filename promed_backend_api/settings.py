from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os
import sentry_sdk
import logging
from sentry_sdk.integrations.django import DjangoIntegration

load_dotenv()

logger = logging.getLogger(__name__)


sentry_sdk.init(
    dsn=os.getenv(
        "SENTRY_DSN",
        "https://e8b8032c2344202bda64fc938e4dc5db@o4509803038113792.ingest.us.sentry.io/4509803039031296"
    ),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
)

TESTING = True
APPEND_SLASH = True  # Changed to False for production consistency

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
# DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
DEBUG = False


RUNNING_ON_AZURE = os.getenv('WEBSITE_SITE_NAME') is not None

AUTH_USER_MODEL = 'provider_auth.User'

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

BASE_CLIENT_URL = 'https://promedhealthplus.com'
LOCAL_CLIENT_URL = 'http://localhost:3000'

AZURE_APP_NAME = 'app-promed-backend-prod-dev'

ALLOWED_HOSTS = [
    f'{AZURE_APP_NAME}.azurewebsites.net',
    f'{AZURE_APP_NAME}.scm.azurewebsites.net',
    '*.westus2-01.azurewebsites.net',
    '169.254.129.6',
    '169.254.129.5',
    '169.254.129.4',
    '169.254.129.3',
    '169.254.129.2',
    'promedhealthplus.com',
    'app-promed-frontend-prod-dev-chfcguavbacqfybc.westus2-01.azurewebsites.net',
    'promedhealth-frontdoor-h4c4bkcxfkduezec.z02.azurefd.net',
    '127.0.0.1',
    '[::1]',
]

if os.getenv('WEBSITE_HOSTNAME'):
    ALLOWED_HOSTS.append(os.getenv('WEBSITE_HOSTNAME'))

CSRF_TRUSTED_ORIGINS = [
    "https://*.azurewebsites.net",
    "https://*.azurefd.net",
    "https://promedhealthplus.com",
    "https://*.promedhealthplus.com",
    "http://localhost:3000",
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
    # 'rest_framework_simplejwt.token_blacklist',
    'anymail',
    'drf_yasg',
    'storages',
    'phonenumber_field',
    'widget_tweaks',
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

CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # 'promed_backend_api.middleware.middleware.RequestLoggingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'provider_auth.backends.EmailBackend',  # Your custom email authentication
    'django.contrib.auth.backends.ModelBackend',  # Keep default as fallback
]

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

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,  # Disable blacklist for now
    'UPDATE_LAST_LOGIN': False,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'william.dev@promedhealthplus.com'

AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')
AZURE_FRONTDOOR_ENDPOINT = 'promedhealth-frontdoor-h4c4bkcxfkduezec.z02.azurefd.net'

AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
AZURE_STATIC_CONTAINER = 'static'
AZURE_MEDIA_CONTAINER = 'media'
AZURE_OVERWRITE_FILES = True

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "promed_backend_api.storage_backends.AzureMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "promed_backend_api.storage_backends.AzureStaticStorage",
    },
}

AZURE_FRONTDOOR_ENDPOINT = 'promedhealth-frontdoor-h4c4bkcxfkduezec.z02.azurefd.net'

USE_FRONTDOOR_FOR_STATIC = os.getenv('USE_FRONTDOOR_FOR_STATIC', 'False') == 'True'

if USE_FRONTDOOR_FOR_STATIC:
    STATIC_URL = f'https://{AZURE_FRONTDOOR_ENDPOINT}/static/'
else:
    STATIC_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_STATIC_CONTAINER}/'

MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_MEDIA_CONTAINER}/'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

logger.info(f"Static files will be served from: {STATIC_URL}")
logger.info(f"Example admin CSS should be at: {STATIC_URL}admin/css/base.css")

logger.info("=" * 80)
logger.info(f"AZURE_ACCOUNT_NAME: {AZURE_ACCOUNT_NAME}")
logger.info(f"STATIC_URL (public): {STATIC_URL}")
logger.info(f"MEDIA_URL (private with SAS): {MEDIA_URL}")
logger.info(f"Example admin CSS: {STATIC_URL}admin/css/base.css")
logger.info("=" * 80)

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Promed Health Plus",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Promed Health Plus",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_brand": "Promed Health Plus",

    # Logo to use for your site, must be present in static files, used for brand on top left
    "site_logo": "/images/logo.png",

    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": None,

    # Logo to use for login form in dark themes (defaults to login_logo)
    "login_logo_dark": None,

    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",

    "site_icon": None,

    # Welcome text on the login screen
    "welcome_sign": "Improving Patient Outcomes with Proven Wound Care Solutions",

    # Copyright on the footer
    "copyright": "Promed Health Plus",

    "search_model": ["auth.User", "auth.Group"],

    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": None,

    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
        
        {"model": "auth.user"}
    ],

    "show_sidebar": True,
    # Whether to aut expand the menu
    "navigation_expanded": True,
    # Hide these apps when generating side menu e.g (auth)
    "hide_apps": [],
    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": [],
    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": ["auth", "books", "books.author", "books.book"],

    # Custom links to append to app groups, keyed on app name
    "custom_links": {
        "books": [{
            "name": "Make Messages", 
            "url": "make_messages", 
            "icon": "fas fa-comments",
            "permissions": ["books.view_book"]
        }]
    },

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
    },
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "related_modal_active": False,
    "custom_css": None,
    "custom_js": None,
    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
    "use_google_fonts_cdn": True,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,

}

# settings.py

JAZZMIN_UI_TWEAKS = {
    # Set the default theme for light mode
    "theme": "flatly", 

    "dark_mode_theme": "darkly", 
    # Other tweaks (optional)
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-teal",        
    "navbar_fixed": True,
    "footer_fixed": False,
}



