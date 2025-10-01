from azure.storage.blob import ContainerClient
import os
from dotenv import load_dotenv
load_dotenv()

container_client = ContainerClient.from_connection_string(
    conn_str=os.getenv('AZURE_CONNECTION_STRING'),
    container_name=os.getenv('AZURE_CONTAINER')
)

for blob in container_client.list_blobs():
    print(blob.name)