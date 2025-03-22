from azure.storage.blob import BlobServiceClient

AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=sebastianblobml;AccountKey=mVq1SpKr/Ezd3odD9iMEROZIcwlK+i/9xz8Pzn5AhhTfTg073jH9aZy01Nr9IxMK5s+yttHVYW3q+ASt6VrnFg==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "blobcontainer"

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

blobs = [blob.name for blob in container_client.list_blobs()]
print("Files in Azure:", blobs)
