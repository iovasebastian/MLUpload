import os

def generate_dockerfile(model_name, model_type, output_dir="dockerfiles"):
    os.makedirs(output_dir, exist_ok=True)

    dockerfile_content = f"""
    # Use Python Base Image
    FROM python:3.10

    # Set working directory
    WORKDIR /backend

    # Install dependencies
    RUN pip install fastapi uvicorn requests numpy \\
        {'onnxruntime' if model_type == 'onnx' else 'scikit-learn'}

    # Copy model file into container
    COPY {model_name} /app/{model_name}
    COPY main.py /backend/main.py

    # Expose port 8000 for FastAPI
    EXPOSE 8000

    # Start FastAPI server
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    """

    # Save the Dockerfile
    dockerfile_path = os.path.join(output_dir, f"dockerfile.{model_name}")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content.strip())

    print(f"✅ Dockerfile generated: {dockerfile_path}")

# Example Usage
generate_dockerfile("modelTestONNX.onnx", "onnx")
generate_dockerfile("modelTest.pkl", "pkl")
