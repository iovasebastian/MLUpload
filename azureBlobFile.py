from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from jwtFile import AuthHandler
import os
import pickle
import onnxruntime as ort
import mysql
# 🔹 Azure Storage Credentials
AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=sebastianblobml;AccountKey=mVq1SpKr/Ezd3odD9iMEROZIcwlK+i/9xz8Pzn5AhhTfTg073jH9aZy01Nr9IxMK5s+yttHVYW3q+ASt6VrnFg==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "blobcontainer"

authHandler = AuthHandler()
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        database="db1"
    )
# 🔹 Initialize Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def upload_file_to_blob(file_name: str, file_content: bytes):
    """
    Uploads a file to Azure Blob Storage.
    """
    try:
        blob_client = container_client.get_blob_client(file_name)
        blob_client.upload_blob(file_content)
        return f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{file_name}"
    except Exception as e:
        return str(e)

def list_blobs():
    """
    Lists all blobs in the container.
    """
    return [blob.name for blob in container_client.list_blobs()]

def download_blob(file_name: str):
    """Downloads a file from Azure Blob Storage."""
    blob_client = container_client.get_blob_client(file_name)

    if not blob_client.exists():  # ✅ Check if the blob exists
        print(f"❌ File '{file_name}' not found in Azure Blob Storage.")
        return None

    print(f"✅ Fetching file: {file_name}")
    return blob_client.download_blob().readall()


def delete_blob(file_name: str):
    """
    Deletes a file from Azure Blob Storage.
    """
    blob_client = container_client.get_blob_client(file_name)
    blob_client.delete_blob()
    return f"{file_name} deleted from Azure Blob Storage."

def load_model(model_name: str):
    """Downloads and loads the model from Azure Blob Storage"""
    try:
        # 🔹 Get Blob Client
        blob_client = container_client.get_blob_client(model_name)
        
        # 🔹 Download Model to Temporary File
        download_path = f"/tmp/{model_name}"
        with open(download_path, "wb") as f:
            f.write(blob_client.download_blob().readall())

        # 🔹 Load Model
        if model_name.endswith(".pkl"):
            with open(download_path, "rb") as f:
                model = pickle.load(f)
        elif model_name.endswith(".onnx"):
            model = ort.InferenceSession(download_path)
        else:
            raise ValueError("Unsupported model format")

        return model

    except Exception as e:
        raise RuntimeError(f"Failed to load model {model_name}: {str(e)}")
    
def list_blobs_per_user(user: dict = Depends(authHandler.authWrapper)):
    print(user)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT modelName FROM models WHERE userId = %s", (user,))
    blob_names = [row["modelName"] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    existing_blobs = []
    for blob_name in blob_names:
        if container_client.get_blob_client(blob_name).exists():
            existing_blobs.append(blob_name)
    return existing_blobs
