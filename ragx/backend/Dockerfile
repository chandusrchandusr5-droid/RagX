FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for C++ extensions (chromadb/hnswlib and PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

# Copy requirements and install dependencies with CPU-only PyTorch protection
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables & start command
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
