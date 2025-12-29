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
RUN pip install -r requirements.txt

# Patch vanna MilvusAgentMemory to handle empty args_json in text memories
RUN sed -i 's/\["\"\],  # args_json (empty for text memories)/\["\{\}"\],  # args_json (empty for text memories)/' /usr/local/lib/python3.11/site-packages/vanna/integrations/milvus/agent_memory.py && \
    sed -i 's/json.loads(result.get("args_json", "{}"))/json.loads(result.get("args_json") or "{}")/' /usr/local/lib/python3.11/site-packages/vanna/integrations/milvus/agent_memory.py && \
    sed -i 's/json.loads(hit.entity.get("args_json", "{}"))/json.loads(hit.entity.get("args_json") or "{}")/' /usr/local/lib/python3.11/site-packages/vanna/integrations/milvus/agent_memory.py

# Copy backend application code
COPY backend/ ./backend/

# Copy assets folder (templates, CSS, JS, fonts)
COPY assets/ ./assets/

# Expose the port the app runs on (default 8000, can be overridden via env at runtime)
EXPOSE 8000

# Run the application with Flask
# Environment variables are loaded from .env via docker-compose or can be set at runtime
CMD ["python", "-m", "backend.main"]
