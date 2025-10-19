from django.conf import settings
from storages.backends.azure_storage import AzureStorage

class AzureMediaStorage(AzureStorage):
    """
    Custom storage backend for media files (user uploads).
    Uses Azure Blob Storage with the 'media' container.
    PRIVATE: Uses SAS tokens for secure access (1 hour expiration).
    """
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = settings.AZURE_MEDIA_CONTAINER
    expiration_secs = 3600  # SAS token expires in 1 hour
    overwrite_files = settings.AZURE_OVERWRITE_FILES

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
    PUBLIC: No SAS tokens needed - container has public blob access.
    """
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_ACCOUNT_KEY
    azure_container = settings.AZURE_STATIC_CONTAINER
    expiration_secs = None  # No expiration - public access
    overwrite_files = settings.AZURE_OVERWRITE_FILES

    def __init__(self, *args, **kwargs):
        if not self.account_name or not self.account_key:
            raise ValueError(
                "Azure Storage credentials not found. "
                "Set AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY environment variables."
            )
        super().__init__(*args, **kwargs)