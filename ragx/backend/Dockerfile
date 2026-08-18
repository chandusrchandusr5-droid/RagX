FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for C++ extensions (chromadb/hnswlib and PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

# Copy requirements and install CPU-only PyTorch to prevent heavy 2.5GB CUDA download timeouts
COPY ragx/backend/requirements.txt* requirements.txt* ./
RUN if [ -f ragx/backend/requirements.txt ]; then cp ragx/backend/requirements.txt requirements.txt; fi && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy application code from root context (ragx/backend) or direct context (.)
COPY ragx/backend/ /app/
COPY . /app/

# Environment variables & start command
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
