"""
Health Check APIs
"""
import logging
import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from backend.storage.vector_db import get_document_count

router = APIRouter(
    prefix="/health-detailed",
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
        "alive": True
    }


@router.get("/ready")
def ready(response: Response):
    """
    Readiness probe — checks whether the service can actually serve traffic
    (i.e. the vector DB is reachable). Returns 503 when not ready so that
    load balancers / orchestrators correctly route traffic away.
    """
    try:
        chunks = get_document_count()
        return {
            "ready": True,
            "database": "connected",
            "knowledge_base_chunks": chunks,
        }
    except Exception:
        logger.exception("Readiness check failed — database unreachable.")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "ready": False,
            "database": "disconnected",
        }


@router.get("/system")
def system():
    uptime = int(time.time() - START_TIME)
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "uptime_seconds": uptime,
    }