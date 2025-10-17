# utils/azure_storage.py
import os
import logging
from io import BytesIO
from datetime import datetime, timedelta

from django.conf import settings
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

logger = logging.getLogger(__name__)

# Initialize blob service client
def get_blob_service_client():
    """Returns a BlobServiceClient instance"""
    try:
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        return BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        logger.error(f"Failed to create BlobServiceClient: {e}")
        raise

# For backward compatibility
blob_service_client = get_blob_service_client()

def clean_string(s):
    """Remove or replace problematic characters in strings"""
    if not s:
        return ""
    # Replace spaces with underscores, remove special chars
    s = s.strip()
    s = s.replace(" ", "_")
    # Keep only alphanumeric, underscore, hyphen, and period
    return "".join(c for c in s if c.isalnum() or c in "._-")

def upload_to_azure_stream(stream, blob_name, container_name='media'):
    """
    Upload a file stream to Azure Blob Storage.
    
    Args:
        stream: File stream (BytesIO object)
        blob_name: Full path/name for the blob (e.g., 'media/provider/file.pdf')
        container_name: Azure container name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting upload to Azure - Blob: {blob_name}, Container: {container_name}")
        
        # Get blob service client
        blob_service_client = get_blob_service_client()
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Reset stream position to beginning
        stream.seek(0)
        
        # Upload the blob
        blob_client.upload_blob(
            stream,
            overwrite=True,
            content_settings={
                'content_type': 'application/pdf'
            }
        )
        
        logger.info(f"✅ Successfully uploaded {blob_name} to Azure Blob Storage")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to upload {blob_name} to Azure: {e}", exc_info=True)
        return False

def generate_sas_url(blob_name, container_name='media', permission='r', expiry_hours=1):
    """
    Generate a SAS URL for accessing a blob.
    
    Args:
        blob_name: Full path/name of the blob
        container_name: Azure container name
        permission: 'r' for read, 'w' for write, etc.
        expiry_hours: How many hours until the URL expires
        
    Returns:
        str: Full URL with SAS token
    """
    try:
        logger.info(f"Generating SAS URL for blob: {blob_name}")
        
        # Get blob service client
        blob_service_client = get_blob_service_client()
        
        # Parse account name from connection string
        account_name = blob_service_client.account_name
        account_key = None
        
        # Extract account key from connection string
        conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
        for part in conn_str.split(';'):
            if part.startswith('AccountKey='):
                account_key = part.split('=', 1)[1]
                break
        
        if not account_key:
            raise ValueError("Could not extract AccountKey from connection string")
        
        # Set expiry time
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True) if permission == 'r' else BlobSasPermissions(write=True),
            expiry=expiry
        )
        
        # Construct full URL
        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        
        logger.info(f"✅ SAS URL generated successfully (expires in {expiry_hours} hours)")
        return sas_url
        
    except Exception as e:
        logger.error(f"❌ Failed to generate SAS URL for {blob_name}: {e}", exc_info=True)
        raise

def delete_blob(blob_name, container_name='media'):
    """
    Delete a blob from Azure Blob Storage.
    
    Args:
        blob_name: Full path/name of the blob to delete
        container_name: Azure container name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Deleting blob: {blob_name} from container: {container_name}")
        
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        blob_client.delete_blob()
        
        logger.info(f"✅ Successfully deleted {blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to delete {blob_name}: {e}", exc_info=True)
        return False

def blob_exists(blob_name, container_name='media'):
    """
    Check if a blob exists in Azure Blob Storage.
    
    Args:
        blob_name: Full path/name of the blob
        container_name: Azure container name
        
    Returns:
        bool: True if exists, False otherwise
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        return blob_client.exists()
        
    except Exception as e:
        logger.error(f"Error checking blob existence: {e}")
        return False

def list_blobs(prefix='', container_name='media'):
    """
    List all blobs in a container with optional prefix filter.
    
    Args:
        prefix: Optional prefix to filter blobs (e.g., 'media/provider-name/')
        container_name: Azure container name
        
    Returns:
        list: List of blob names
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)
        
        blob_list = []
        for blob in container_client.list_blobs(name_starts_with=prefix):
            blob_list.append(blob.name)
        
        return blob_list
        
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        return []