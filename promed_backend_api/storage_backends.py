# promed_backend_api/storage_backends.py
from storages.backends.azure_storage import AzureStorage
from django.conf import settings
import os


class AzureMediaStorage(AzureStorage):
    """
    Custom storage backend for media files (user uploads).
    Uses Azure Blob Storage with the 'media' container.
    """
    account_name = getattr(settings, 'AZURE_ACCOUNT_NAME', None) or os.getenv('AZURE_ACCOUNT_NAME')
    account_key = getattr(settings, 'AZURE_ACCOUNT_KEY', None) or os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = 'media'
    expiration_secs = None
    overwrite_files = True

    def __init__(self, *args, **kwargs):
        if not self.account_name or not self.account_key:
            raise ValueError(
                "Azure Storage credentials not found. "
                "Set AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY environment variables."
            )
        super().__init__(*args, **kwargs)


class AzureStaticStorage(AzureStorage):
    """
    Custom storage backend for static files (CSS, JS, admin assets).
    Uses Azure Blob Storage with the 'static' container.
    """
    account_name = getattr(settings, 'AZURE_ACCOUNT_NAME', None) or os.getenv('AZURE_ACCOUNT_NAME')
    account_key = getattr(settings, 'AZURE_ACCOUNT_KEY', None) or os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = 'static'
    expiration_secs = None
    overwrite_files = True  # Overwrite to avoid version conflicts

    def __init__(self, *args, **kwargs):
        if not self.account_name or not self.account_key:
            raise ValueError(
                "Azure Storage credentials not found. "
                "Set AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY environment variables."
            )
        super().__init__(*args, **kwargs)