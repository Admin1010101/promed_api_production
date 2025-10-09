# promed_backend_api/storage_backends.py
from storages.backends.azure_storage import AzureStorage
from django.conf import settings


class AzureMediaStorage(AzureStorage):
    """
    Custom storage backend for media files (user uploads).
    Uses Azure Blob Storage.
    """
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = 'media'
    expiration_secs = None
    overwrite_files = True  # Allow overwriting files with the same name


class AzureStaticStorage(AzureStorage):
    """
    Custom storage backend for static files (CSS, JS, admin assets).
    
    NOTE: This is currently NOT being used in production.
    We're using WhiteNoise instead (see settings.py STORAGES config).
    
    This class is kept here for reference in case you want to 
    switch to Azure-based static file serving in the future.
    """
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = 'static'
    expiration_secs = None