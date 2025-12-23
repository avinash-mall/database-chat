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

# Copy backend application code
COPY backend/ ./backend/

# Create directory for ChromaDB persistence
RUN mkdir -p /app/chroma_db

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables with defaults
ENV VANNA_HOST=0.0.0.0
ENV VANNA_PORT=8000
ENV VANNA_LOG_LEVEL=info

# Run the application
CMD ["python", "-m", "backend.main"]
