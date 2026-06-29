from pathlib import Path
import os

# ==========================
# PROJECT PATHS
# ==========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "storage" / "data"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads" / "pdfs"
VECTOR_DB_DIR = BASE_DIR / "storage" / "database" / "chroma_db"
LOG_DIR = BASE_DIR / "logs"

# ==========================
# OLLAMA SETTINGS
# ==========================
# NOTE: llama3.1:8b is heavy (~6GB RAM) and can freeze laptops/Macs.
# Default to a lightweight model so the app stays responsive.
# Override anytime: OLLAMA_MODEL=llama3.1:8b python -m uvicorn backend.app:app
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ==========================
# EMBEDDING MODEL
# ==========================
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ==========================
# RAG SETTINGS
# ==========================
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K_RESULTS = 2

# ==========================
# SECURITY
# ==========================
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_FILE_TYPES = [".pdf"]

# ==========================
# CREATE DIRECTORIES
# ==========================
for directory in [DATA_DIR, UPLOAD_DIR, VECTOR_DB_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
