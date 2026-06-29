"""
Health Check APIs
"""
import logging
import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from backend.storage.vector_db import get_document_count
from backend.core.llm import check_ollama

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

logger = logging.getLogger(__name__)

START_TIME = time.time()


@router.get("/")
def health():
    return {
        "status": "healthy",
        "service": "CIMS SAGE",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live")
def live():
    return {
        "status": "ok",
        "alive": True,
        "service": "CIMS SAGE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def ready(response: Response):
    """Readiness probe — checks whether the vector DB is reachable."""
    try:
        chunks = get_document_count()
        return {
            "ready": True,
            "status": "ready",
            "database": "connected",
            "knowledge_base_chunks": chunks,
        }
    except Exception:
        logger.exception("Readiness check failed — database unreachable.")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "ready": False,
            "status": "not_ready",
            "database": "disconnected",
        }


@router.get("/llm")
def llm_health(response: Response):
    """Diagnostic for the Ollama LLM: reachability + installed models."""
    info = check_ollama()
    if not info.get("reachable"):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return info


@router.get("/system")
def system():
    uptime = int(time.time() - START_TIME)
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "uptime_seconds": uptime,
    }
