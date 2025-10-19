import os
import django
from io import BytesIO
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promed_backend_api.settings')
django.setup()

from django.conf import settings
from utils.azure_storage import upload_to_azure_stream, blob_exists, generate_sas_url

def test_azure_upload():
    """Test Azure Blob Storage upload functionality"""
    
    print("=" * 80)
    print("TESTING AZURE BLOB STORAGE UPLOAD")
    print("=" * 80)
    
    # Check credentials
    print(f"\n1. Checking Azure credentials...")
    print(f"   AZURE_ACCOUNT_NAME: {settings.AZURE_ACCOUNT_NAME}")
    print(f"   AZURE_MEDIA_CONTAINER: {settings.AZURE_MEDIA_CONTAINER}")
    print(f"   Connection string configured: {bool(settings.AZURE_STORAGE_CONNECTION_STRING)}")
    
    # Create test file
    print(f"\n2. Creating test PDF content...")
    test_content = b"%PDF-1.4\nTest PDF content for upload verification\n"
    test_stream = BytesIO(test_content)
    
    # Generate blob path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_path = f"media/test/test-upload-{timestamp}.pdf"
    container_name = settings.AZURE_MEDIA_CONTAINER
    
    print(f"   Blob path: {blob_path}")
    print(f"   Container: {container_name}")
    print(f"   Content size: {len(test_content)} bytes")
    
    # Upload
    print(f"\n3. Uploading to Azure Blob Storage...")
    try:
        result = upload_to_azure_stream(test_stream, blob_path, container_name)
        
        if result:
            print(f"   ✅ Upload successful!")
        else:
            print(f"   ❌ Upload failed!")
            return False
            
    except Exception as e:
        print(f"   ❌ Upload error: {str(e)}")
        return False
    
    # Verify
    print(f"\n4. Verifying blob exists...")
    try:
        exists = blob_exists(blob_path, container_name)
        if exists:
            print(f"   ✅ Blob verified in Azure!")
        else:
            print(f"   ❌ Blob not found in Azure!")
            return False
    except Exception as e:
        print(f"   ❌ Verification error: {str(e)}")
        return False
    
    # Generate SAS URL
    print(f"\n5. Generating SAS URL...")
    try:
        sas_url = generate_sas_url(blob_path, container_name, permission='r', expiry_hours=1)
        print(f"   ✅ SAS URL generated!")
        print(f"   URL: {sas_url[:100]}...")
    except Exception as e:
        print(f"   ❌ SAS URL error: {str(e)}")
        return False
    
    print(f"\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Azure upload is working correctly!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    test_azure_upload()