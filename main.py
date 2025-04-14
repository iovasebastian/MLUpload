from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from azureBlobFile import list_blobs_admin, upload_file_to_blob, list_blobs, download_blob, delete_blob, load_model, list_blobs_per_user
from datetime import datetime
from passhash import hashPassword, verifyPassword
from jwtFile import AuthHandler
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request, Path
from fastapi.responses import JSONResponse
from fastapi import Header
import subprocess
import requests
import json
import onnxruntime as ort
import numpy as np
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.info("NEW MODEL !!!!!!!!!!")
app = FastAPI()
authHandler = AuthHandler()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"], 
    allow_headers=["Authorization", "Content-Type"], 
)

JENKINS_URL = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")
SQL_HOST = os.getenv("SQL_HOST")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DATABASE = os.getenv("SQL_DATABASE")

def get_db_connection():
    return mysql.connector.connect(
        host= SQL_HOST,
        user= SQL_USER,
        password= SQL_PASSWORD,
        database= SQL_DATABASE
    )

class User(BaseModel):
    email:str
    password:str
    role:str
class UserLogin(BaseModel):
    email:str
    password:str
class MetaDataFile(BaseModel):
    modelName: str
    creationDate: datetime
    userId: int
class PredictionInput(BaseModel):
    data: dict

@app.post("/createaccount")
def create_user(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    plainPassword = user.password
    hashedPassword = hashPassword(plainPassword)
    try:
        cursor.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", (user.email, hashedPassword, 'user'))
        conn.commit()
        print('created')
        return {"message": "User created successfully!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()
@app.post("/login")
def login(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email, password, role FROM users WHERE email = %s", (user.email,))
        userFound = cursor.fetchone()
        print(userFound)
        if not userFound:
            raise HTTPException(status_code=404, detail=f"User {user.email} not found")

        if verifyPassword(user.password, userFound["password"]):
            token = authHandler.encodeToken(userFound["id"], userFound["role"])
            response = JSONResponse(content={"id": userFound["id"], "role": userFound["role"], "access_token": token })
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=True,
                samesite="None"
            )
            return response
        else:
            raise HTTPException(status_code=401, detail="Wrong password")
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred, {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.post("/create")
def addMetaData(metaData: MetaDataFile):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO models (modelName, creationDate, userId) VALUES (%s, %s, %s)", (metaData.modelName, metaData.creationDate, metaData.userId))
        conn.commit()
        print('created')
        return {"message": "Metadata added successfully!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed adding!{str(e)}")

@app.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out successfully!"})
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True, 
        samesite="None"
    )

    return response

@app.get("/check-admin")
def check_admin(user: dict = Depends(authHandler.authWrapper)):
    if not user: 
        return JSONResponse(content={"detail": "Not authenticated"}, status_code=403)

    if user["role"] != "admin": 
        return JSONResponse(content={"detail": "Access denied, not an admin"}, status_code=403)

    return {"message": "User is an admin", "id": user["id"], "role": user["role"]}

@app.get("/checkUnique/{modelName:path}")
def checkUnique(modelName:str = Path(...), user: dict = Depends(authHandler.authWrapper)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT modelName FROM models WHERE modelName = %s", (modelName,))
        result = cursor.fetchone()
        logger.info(result)
        if result:
            return False
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing string: {str(e)}")
@app.get("/getIp")
def getIp(modelName:str, user: dict = Depends(authHandler.authWrapper)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT modelIp FROM models WHERE modelName = %s", (modelName,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Model not found or IP not available")

        return {"ip": result["modelIp"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

@app.get("/debug-token-header")
def debug_token_header(request: Request):
    return {
        "auth_header": request.headers.get("Authorization"),
        "token_from_header": request.headers.get("Authorization").split("Bearer ")[1] if request.headers.get("Authorization") else None
    }

@app.get("/jenkins/status/{job_name}")
def get_jenkins_status(job_name: str):
    try:
        url = f"http://localhost:8080/job/{job_name}/lastBuild/wfapi/describe"
        response = requests.get(url, auth=(JENKINS_USERNAME, JENKINS_TOKEN))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jenkins error: {str(e)}")
    
@app.post("/deploy")
def deploy(model: str = Query(...), type: str = Query(...)):
    try:
        response = requests.post(
            JENKINS_URL,
            params={
                "MODEL_NAME": model,
                "MODEL_TYPE": type
            },
            auth=(JENKINS_USERNAME, JENKINS_TOKEN)
        )

        if response.status_code == 201:
            return {"message": "Jenkins job triggered successfully"}
        else:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": response.text}
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

#AZURE CRUD

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_content = await file.read()
    file_url = upload_file_to_blob(file.filename, file_content)
    return {"message": "File uploaded successfully", "url": file_url}

# List Files in Azure Blob Storage
@app.get("/list/")
def list_files(userId, user: dict = Depends(authHandler.authWrapper)):
    """API function that returns only the user's files."""
    user_blobs = list_blobs_per_user(userId)
    return {"files": user_blobs}

@app.get("/listAdmin/")
def list_files(userId, user: dict = Depends(authHandler.authWrapper)):
    """API function that returns only the user's files."""
    user_blobs = list_blobs_admin(userId)
    return {"files": user_blobs}

#def list_files():
#   blobs = list_blobs()
#    return {"files": blobs}

# Download a File
@app.get("/download/{file_name}")
def download_file(file_name: str):
    try:
        file_content = download_blob(file_name)
        return {"file_name": file_name, "content": file_content.decode()}  # Convert bytes to string
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

# Delete a File
@app.delete("/delete/{file_name}")
def delete_file(file_name: str):
    try:
        message = delete_blob(file_name)
        model_name = file_name.split('.')[0].lower()
        subprocess.run(["kubectl", "delete", "deployment", f"{model_name}-deployment"], check=False)
        subprocess.run(["kubectl", "delete", "svc", f"{model_name}-service"], check=False)
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM models WHERE modelName = %s"
        cursor.execute(query, (file_name,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": message, "dbmessage": f"✅ DB entry for '{model_name}' deleted."}
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    
#Prediction with onxx and pickle
@app.post("/predict/{model_name:path}")
async def predict(model_name: str, input_data: PredictionInput, user: dict = Depends(authHandler.authWrapper)):
    """Run prediction using the uploaded model"""
    try:
        model = load_model(model_name)
        requestDate = datetime.now().strftime("%c")
        if model_name.endswith(".pkl"):
            # Scikit-Learn Model
            prediction = model.predict([list(input_data.data.values())]).tolist()

        
        elif model_name.endswith(".onnx"):
    # ONNX Model
            inputs_dict = input_data.data 

            ort_inputs = {}
            for input_tensor in model.get_inputs():
                input_name = input_tensor.name  # Get input name
                input_dtype = input_tensor.type  # Get expected ONNX dtype
                print(f"Processing input: {input_name}, Expected Type: {input_dtype}")

                dtype_map = {
                    "tensor(int64)": np.int64,
                    "tensor(int32)": np.int32,
                    "tensor(float)": np.float32,  
                    "tensor(float32)": np.float32,
                    "tensor(float64)": np.float64
                }

                np_dtype = dtype_map.get(input_dtype.lower())
                if np_dtype is None:
                    raise ValueError(f"Unsupported ONNX input type: {input_dtype}")

                # Convert input data dynamically
                if input_name in inputs_dict:
                    ort_inputs[input_name] = np.array(inputs_dict[input_name], dtype=np_dtype)
                else:
                    raise ValueError(f"Missing expected input: {input_name}")

            prediction = model.run(None, ort_inputs)[0].tolist()
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT modelId FROM models WHERE modelName = %s", (model_name,))
                result = cursor.fetchone()
                if not result or not result.get('modelId'):
                    raise HTTPException(status_code=404, detail="Model not found")
                modelId = result['modelId']
                cursor.execute("INSERT INTO modelLogs (actionName, actionDescription, actionTime, modelId) VALUES (%s, %s, %s, %s)", ("POST", "Post request", requestDate, modelId))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error uploading logs into the database {str(e)}")

        else:
            raise HTTPException(status_code=400, detail="Invalid model format")

        return {"model": model_name, "prediction": prediction}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/predict/{model_name}")
async def get_model_input(model_name: str):
    try:
        model = load_model(model_name)  #loads the file from Blob
        extension = os.path.splitext(model_name)[-1].lower()

        if extension == ".onnx":
            # Handle ONNX model
            input_details = [{"name": input.name, "shape": input.shape} for input in model.get_inputs()]
            output_details = [{"name": output.name, "shape": output.shape} for output in model.get_outputs()]

            return {
                "type": "onnx",
                "inputs": input_details,
                "outputs": output_details
            }

        elif extension == ".pkl":
            # Handle Pickle model
            input_features = getattr(model, "feature_names_in_", None)

            if input_features is None:
                raise Exception("Cannot determine input features for this pickle model.")

            return {
                "type": "pickle",
                "inputs": list(input_features),
                "outputs": [str(model.__class__)]
            }

        else:
            raise Exception(f"Unsupported model extension: {extension}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting model details: {str(e)}")
    