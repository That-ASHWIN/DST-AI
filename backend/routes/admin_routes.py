"""
Admin APIs
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from backend.storage.vector_db import (
    clear_database,
    get_document_count,
)

COLLECTION_NAME = "cims_knowledge_base"

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

logger = logging.getLogger(__name__)


@router.get("/stats")
def stats():
    return {
        "documents": get_document_count(),
        "database": "ChromaDB",
        "collection": COLLECTION_NAME,
    }


@router.delete("/clear")
def clear_db(
    confirm: bool = Query(
        False,
        description="Must be explicitly set to true to actually clear the database. "
                     "Safety guard against accidental deletion.",
    ),
):
    """
    Deletes ALL chunks from the vector database.

    This is destructive and irreversible — requires `?confirm=true` to run.
    Calling without it returns 400 and leaves the database untouched.
    """
    if not confirm:
        logger.warning("Clear DB called without confirmation — aborting, no data deleted.")
        raise HTTPException(
            status_code=400,
            detail="This will permanently delete all chunks. "
                   "Pass ?confirm=true to proceed.",
        )

    before = get_document_count()
    logger.warning("Clearing database. %s chunk(s) will be deleted.", before)

    clear_database()

    after = get_document_count()
    logger.info("Database cleared. Deleted %s chunk(s), %s remaining.", before, after)

    return {
        "success": True,
        "deleted_chunks": before,
        "remaining_chunks": after,
    }


@router.get("/health")
def health():
    try:
        chunks = get_document_count()
        return {
            "status": "healthy",
            "database": "connected",
            "knowledge_base_chunks": chunks,
            "service": "CIMS SAGE API",
        }
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Database unavailable.",
        )