from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from azureBlobFile import upload_file_to_blob, list_blobs, download_blob, delete_blob, load_model, list_blobs_per_user
from datetime import datetime
from passhash import hashPassword, verifyPassword
from jwtFile import AuthHandler
from fastapi.security import OAuth2PasswordBearer
import json
import onnxruntime as ort
import numpy as np

app = FastAPI()
authHandler = AuthHandler()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://quick-cougars-obey.loca.lt"],  # ✅ Replace with your frontend URL
    allow_credentials=True,  # ✅ Required for cookies (withCredentials: true)
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"],  # ✅ Only allow necessary methods
    allow_headers=["Authorization", "Content-Type"],  # ✅ Allow necessary headers
)

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="1234",
        database="db1"
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
        raise HTTPException(status_code=500, detail="Failed adding!")

@app.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out successfully!"})
    # ✅ Remove token from cookies
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,  # Change to True for production with HTTPS
        samesite="None"
    )

    return response

@app.get("/check-admin")
def check_admin(user: dict = Depends(authHandler.authWrapper)):
    if not user:  # ✅ Ensure that user is actually present
        return JSONResponse(content={"detail": "Not authenticated"}, status_code=403)

    if user["role"] != "admin":  # ✅ Ensure only admins can access
        return JSONResponse(content={"detail": "Access denied, not an admin"}, status_code=403)

    return {"message": "User is an admin", "id": user["id"], "role": user["role"]}

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

#AZURE CRUD

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_content = await file.read()
    file_url = upload_file_to_blob(file.filename, file_content)
    return {"message": "File uploaded successfully", "url": file_url}

# 🔹 List Files in Azure Blob Storage
@app.get("/list/")
def list_files(userId):
    """API function that returns only the user's files."""
    user_blobs = list_blobs_per_user(userId)
    return {"files": user_blobs}

#def list_files():
#   blobs = list_blobs()
#    return {"files": blobs}

# 🔹 Download a File
@app.get("/download/{file_name}")
def download_file(file_name: str):
    try:
        file_content = download_blob(file_name)
        return {"file_name": file_name, "content": file_content.decode()}  # Convert bytes to string
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

# 🔹 Delete a File
@app.delete("/delete/{file_name}")
def delete_file(file_name: str):
    try:
        message = delete_blob(file_name)
        return {"message": message}
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    
#Prediction with onxx and pickle
@app.post("/predict/{model_name}")
async def predict(model_name: str, input_data: PredictionInput, user: dict = Depends(authHandler.authWrapper)):
    """Run prediction using the uploaded model"""
    try:
        model = load_model(model_name)

        if model_name.endswith(".pkl"):
            # ✅ Scikit-Learn Model
            prediction = model.predict([list(input_data.data.values())]).tolist()

        
        elif model_name.endswith(".onnx"):
    # ✅ ONNX Model
            inputs_dict = input_data.data  # Assuming this is already a dict with needed keys

            # ✅ Dynamically fetch model input names & data types
            ort_inputs = {}
            for input_tensor in model.get_inputs():
                input_name = input_tensor.name  # Get input name
                input_dtype = input_tensor.type  # Get expected ONNX dtype
                print(f"Processing input: {input_name}, Expected Type: {input_dtype}")

                # ✅ Match ONNX dtype to NumPy dtype
                dtype_map = {
                    "tensor(int64)": np.int64,
                    "tensor(int32)": np.int32,
                    "tensor(float)": np.float32,  # ✅ Fix for tensor(float)
                    "tensor(float32)": np.float32,
                    "tensor(float64)": np.float64
                }

                # ✅ Validate & assign dtype
                np_dtype = dtype_map.get(input_dtype.lower())
                if np_dtype is None:
                    raise ValueError(f"Unsupported ONNX input type: {input_dtype}")

                # ✅ Convert input data dynamically
                if input_name in inputs_dict:
                    ort_inputs[input_name] = np.array(inputs_dict[input_name], dtype=np_dtype)
                else:
                    raise ValueError(f"Missing expected input: {input_name}")

            # ✅ Run inference
            prediction = model.run(None, ort_inputs)[0].tolist()

        else:
            raise HTTPException(status_code=400, detail="Invalid model format")

        return {"model": model_name, "prediction": prediction}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/predict/{model_name}")
async def getModelInput(model_name: str):
    try:
        model = load_model(model_name)  # Now returns `InferenceSession`
        input_details = [{"name": input.name, "shape": input.shape} for input in model.get_inputs()]

        # ✅ Extract Outputs
        output_details = [{"name": output.name, "shape": output.shape} for output in model.get_outputs()]

        return {
            "inputs": input_details,
            "outputs": output_details
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting model details: {str(e)}")
    