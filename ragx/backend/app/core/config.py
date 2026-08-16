import os
from pathlib import Path

# Base Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
TRASH_DIR = DATA_DIR / "trash"
CHROMA_DIR = DATA_DIR / "chroma_db"
REGISTRY_FILE = DATA_DIR / "document_registry.json"

# Create directories if they do not exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TRASH_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "RAGX — Data Quality & Hallucination Detection for RAG Systems"
    API_PREFIX: str = "/api"
    
    # Storage Paths
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    TRASH_DIR: Path = TRASH_DIR
    CHROMA_DIR: Path = CHROMA_DIR
    REGISTRY_FILE: Path = REGISTRY_FILE
    EVAL_HISTORY_FILE: Path = DATA_DIR / "evaluation_history.json"


    
    # Vector DB Settings
    COLLECTION_NAME: str = "ragx_documents"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # Chunking Configuration
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 3

    # Data Quality Evaluation Weights & Thresholds
    WEIGHT_EXTRACTION: float = 0.35
    WEIGHT_DIVERSITY: float = 0.30
    WEIGHT_CONSISTENCY: float = 0.35
    CHUNK_DUPLICATE_THRESHOLD: float = 0.90
    
    # Phase 3 RAG Answer Reliability Evaluator Weights
    WEIGHT_CLAIM_SUPPORT: float = 0.50
    WEIGHT_CITATION_COVERAGE: float = 0.25
    WEIGHT_RETRIEVAL_SIMILARITY: float = 0.25

    
    # LLM Settings (Ollama local / fallback API)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    USE_OLLAMA: bool = True

settings = Settings()

