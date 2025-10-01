from storages.backends.azure_storage import AzureStorage
from django.conf import settings
import os

AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')

print('AZURE_ACCOUNT_NAME:', AZURE_ACCOUNT_NAME)
print('AZURE_ACCOUNT_KEY:', AZURE_ACCOUNT_KEY)

# --- 1. AzureMediaStorage (For Private PHI/PDFs) ---
class AzureMediaStorage(AzureStorage):
    account_name = AZURE_ACCOUNT_NAME
    account_key = AZURE_ACCOUNT_KEY
    azure_container = "media"
    expiration_secs = None
    # Make media files private
    overwrite_files = False

    def get_default_settings(self):
        settings = super().get_default_settings()
        # Ensure media files are private (no public access)
        settings['blob_public_access'] = None
        return settings


class AzureStaticStorage(AzureStorage):
    account_name = AZURE_ACCOUNT_NAME
    account_key = AZURE_ACCOUNT_KEY
    azure_container = "static"
    expiration_secs = None
    overwrite_files = True

    def get_default_settings(self):
        settings = super().get_default_settings()
        # Make static files publicly accessible
        settings['blob_public_access'] = 'blob'
        return settings