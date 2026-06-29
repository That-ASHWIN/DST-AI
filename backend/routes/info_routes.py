"""
Knowledge Base APIs
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from backend.config import UPLOAD_DIR
from backend.storage.vector_db import get_document_count

router = APIRouter(
    prefix="/admin",
    tags=["Knowledge Base"],
)

logger = logging.getLogger(__name__)


def _list_pdfs() -> List[Path]:
    """
    Returns all PDFs in UPLOAD_DIR, matched case-insensitively (.pdf / .PDF).
    Skips any file that disappears between listing and stat-ing (race condition
    with concurrent uploads/deletes) instead of crashing the request.
    """
    upload_dir = Path(UPLOAD_DIR)
    if not upload_dir.exists():
        logger.warning("UPLOAD_DIR does not exist: %s", upload_dir)
        return []

    seen = {}
    for pattern in ("*.pdf", "*.PDF"):
        for f in upload_dir.glob(pattern):
            seen[f.name] = f
    return list(seen.values())


def _safe_stat_size(path: Path) -> int:
    """Returns file size in bytes, or 0 if the file vanished mid-request."""
    try:
        return path.stat().st_size
    except FileNotFoundError:
        logger.warning("File disappeared while reading stats: %s", path.name)
        return 0


@router.get("/info")
def knowledge_base_info():
    pdfs = _list_pdfs()
    total_size = sum(_safe_stat_size(f) for f in pdfs)

    try:
        total_chunks = get_document_count()
    except Exception:
        logger.exception("Failed to fetch document count for /admin/info.")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve knowledge base stats. Database unavailable.",
        )

    return {
        "total_pdfs": len(pdfs),
        "total_chunks": total_chunks,
        "storage_size_mb": round(total_size / (1024 * 1024), 2),
        "database": "ChromaDB",
        "collection": "cims_knowledge_base",
    }


@router.get("/files")
def uploaded_files():
    pdfs = _list_pdfs()
    files = []
    total_size = 0

    for pdf in pdfs:
        size_bytes = _safe_stat_size(pdf)
        total_size += size_bytes
        try:
            modified = datetime.fromtimestamp(pdf.stat().st_mtime).isoformat()
        except FileNotFoundError:
            modified = None

        files.append(
            {
                "name": pdf.name,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "modified_at": modified,
            }
        )

    # Most recently modified first — most useful default for an admin UI.
    # Files with unknown modified time (None) sort last.
    files.sort(key=lambda f: f["modified_at"] or "", reverse=True)

    return {
        "count": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files": files,
    }