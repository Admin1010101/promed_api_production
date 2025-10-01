from storages.backends.azure_storage import AzureStorage
import os

class AzureMediaStorage(AzureStorage):
    account_name = os.getenv('AZURE_ACCOUNT_NAME')  # Must be in environment
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = os.getenv('AZURE_CONTAINER')  # like 'media'
    expiration_secs = None