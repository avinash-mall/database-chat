# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Oracle client and other libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ChromaDB ONNX model to bake it into the image
# Download the model directly from ChromaDB's S3 bucket and extract it
RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2 && \
    curl -L https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz -o /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz && \
    tar -xzf /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz -C /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/ && \
    rm /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz && \
    chmod -R 755 /root/.cache/chroma

# Copy backend application code
COPY backend/ ./backend/

# Copy assets folder (templates, CSS, JS, fonts)
COPY assets/ ./assets/

# Create directory for ChromaDB persistence
RUN mkdir -p /app/chroma_db

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables with defaults
ENV VANNA_HOST=0.0.0.0
ENV VANNA_PORT=8000
ENV VANNA_LOG_LEVEL=info
ENV FLASK_ENV=production

# Run the application with Flask
CMD ["python", "-m", "backend.main"]
