import os
import logging
from datetime import datetime, timedelta
from io import BytesIO
from django.conf import settings
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

logger = logging.getLogger(__name__)


def get_blob_service_client():
    """Get Azure Blob Service Client"""
    connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")
    return BlobServiceClient.from_connection_string(connection_string)


def upload_to_azure_stream(stream, blob_path, container_name):
    """
    Upload a file stream to Azure Blob Storage.
    
    Args:
        stream: File-like object (BytesIO or file handle)
        blob_path: Path within the container (e.g., "media/provider/onboarding/form.pdf")
        container_name: Name of the Azure container
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Reset stream position to beginning
        stream.seek(0)
        
        # Get blob service client
        blob_service_client = get_blob_service_client()
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_path
        )
        
        # Upload the blob
        blob_client.upload_blob(stream, overwrite=True)
        
        logger.info(f"Successfully uploaded to Azure: {blob_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload to Azure: {str(e)}", exc_info=True)
        return False


def blob_exists(blob_path, container_name):
    """
    Check if a blob exists in Azure Storage.
    
    Args:
        blob_path: Path to the blob
        container_name: Container name
        
    Returns:
        bool: True if exists, False otherwise
    """
    try:
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )
        return blob_client.exists()
    except Exception as e:
        logger.error(f"Error checking blob existence: {str(e)}")
        return False


def generate_sas_url(blob_name, container_name, permission='r', expiry_hours=1):
    """
    Generate a SAS URL for a blob.
    
    Args:
        blob_name: Name/path of the blob
        container_name: Container name
        permission: Permission string ('r' for read, 'w' for write, etc.)
        expiry_hours: Hours until the SAS token expires
        
    Returns:
        str: Full URL with SAS token
    """
    try:
        account_name = settings.AZURE_ACCOUNT_NAME
        account_key = settings.AZURE_ACCOUNT_KEY
        
        if not account_name or not account_key:
            raise ValueError("Azure credentials not configured")
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True) if permission == 'r' else BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        # Construct full URL
        blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        
        return blob_url
        
    except Exception as e:
        logger.error(f"Failed to generate SAS URL: {str(e)}", exc_info=True)
        raise