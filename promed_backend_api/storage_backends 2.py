from storages.backends.azure_storage import AzureStorage
from django.conf import settings
import os

class AzureMediaStorage(AzureStorage):
    print('this is getting here...')
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = "media"
    expiration_secs = None

class AzureStaticStorage(AzureStorage):
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = "static"
    expiration_secs = None