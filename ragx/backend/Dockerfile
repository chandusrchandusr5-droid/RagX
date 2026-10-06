FROM python:3.11-slim

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
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
