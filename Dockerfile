# Use Python Base Image
    FROM python:3.10

    # Set working directory
    WORKDIR /backend

    # Install dependencies
    RUN pip install fastapi uvicorn requests numpy mysql-connector-python \
        onnxruntime pyjwt azure-storage-blob passlib python-multipart

    # Copy model file into container
    COPY model.onnx /backend/model.onnx
    COPY ./main.py /backend/main.py
    COPY ./azureBlobFile.py /backend/azureBlobFile.py
    COPY ./passhash.py /backend/passhash.py
    COPY ./jwtFile.py /backend/jwtFile.py

    # Expose port 8000 for FastAPI
    EXPOSE 8000

    # Start FastAPI server
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]