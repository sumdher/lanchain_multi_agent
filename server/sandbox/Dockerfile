# Use a lightweight Python base image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-pip \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install python-multipart fastapi uvicorn jupyter-client nbformat ipykernel
RUN python3 -m ipykernel install --user
RUN pip install pandas numpy matplotlib scipy seaborn scikit-learn pyarrow tabulate openpyxl xlrd

# Create necessary directories
RUN mkdir -p /mnt/data /mnt/jupyter_sessions /workspace

# Set environment variables for mounted volumes
ENV DATA_DIR=/mnt/data
ENV JUPYTER_SESSIONS_DIR=/mnt/jupyter_sessions

# Copy the FastAPI server script into the container
COPY fastapi_jupyter_server.py /workspace/fastapi_jupyter_api.py

# Set the working directory
WORKDIR /workspace

# Expose the FastAPI server port
EXPOSE 5002

# Use Python to start the FastAPI server
CMD ["python3.12", "-m", "uvicorn", "fastapi_jupyter_api:app", "--host", "0.0.0.0", "--port", "5002"]
