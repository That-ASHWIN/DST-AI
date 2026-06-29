import ipaddress
import logging
import socket

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from backend.ingestion.url_loader import ingest_url

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


class URLRequest(BaseModel):
    url: HttpUrl


def _is_safe_url(url: str) -> bool:
    """
    Resolve the URL's hostname and reject it if it points to a private,
    loopback, or link-local address. Without this check, the server can be
    tricked into fetching internal/local addresses (SSRF) — e.g. a malicious
    user submitting "http://127.0.0.1:11434" or "http://169.254.169.254"
    (cloud metadata endpoint) instead of a real external webpage.
    """
    from urllib.parse import urlparse

    hostname = urlparse(url).hostname
    if not hostname:
        return False

    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError):
        # Can't resolve the hostname at all — treat as unsafe rather than
        # letting the downstream request hang or fail unpredictably.
        return False

    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
        return False

    return True


@router.post("/url")
async def upload_url(request: URLRequest):
    """
    Download a webpage, extract text,
    create embeddings and store into ChromaDB.
    """
    url_str = str(request.url)

    if not _is_safe_url(url_str):
        raise HTTPException(
            status_code=400,
            detail="This URL cannot be accessed (private, local, or invalid address).",
        )

    try:
        chunks = ingest_url(url_str)
        if chunks == 0:
            raise HTTPException(
                status_code=422,
                detail="No content could be extracted from this URL.",
            )
        return {
            "success": True,
            "url": url_str,
            "chunks_indexed": chunks,
            "message": "URL indexed successfully.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"URL ingestion failed for {url_str!r}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch or process this URL.",
        ) from e