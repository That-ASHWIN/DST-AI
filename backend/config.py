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
# OLLAMA SETTINGS (local development)
# ==========================
# NOTE: llama3.1:8b is heavy (~6GB RAM) and can freeze laptops/Macs.
# Default to a lightweight model so the app stays responsive.
# Override anytime: OLLAMA_MODEL=llama3.1:8b python -m uvicorn backend.app:app
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ==========================
# HOSTED LLM (for 24/7 cloud deploy - no local Ollama / laptop needed)
# ==========================
# If LLM_API_KEY is set, the app talks to a hosted OpenAI-compatible chat API
# (e.g. Groq's free API) instead of local Ollama. This lets the chatbot run on
# a cloud server around the clock, even when your laptop is off.
#   - Get a free key at https://console.groq.com/keys
#   - Set env vars: LLM_API_KEY=...  (LLM_BASE_URL / LLM_MODEL are optional)
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
USE_HOSTED_LLM = bool(LLM_API_KEY)

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
