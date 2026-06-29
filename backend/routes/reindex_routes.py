"""
Re-index APIs
Rebuilds the knowledge base from all uploaded PDFs.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from backend.ingestion.pdf_loader import ingest_all_pdfs
from backend.storage.vector_db import (
    clear_database,
    get_document_count,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

logger = logging.getLogger(__name__)


@router.post("/reindex")
def reindex_database(
    confirm: bool = Query(
        False,
        description="Must be explicitly set to true to actually re-index. "
                     "Safety guard — this clears the existing knowledge base first.",
    ),
):
    """
    Clears the vector database and rebuilds it using every PDF present in
    storage/uploads/pdfs.

    Destructive — requires `?confirm=true` to run. Calling without it
    returns 400 and leaves the database untouched.

    If ingestion fails or finds zero chunks after clearing, the previous
    knowledge base is NOT restored automatically — check `current_chunks`
    in the response (or re-run /admin/reindex) if this happens.
    """
    if not confirm:
        logger.warning("Re-index called without confirmation — aborting, no changes made.")
        raise HTTPException(
            status_code=400,
            detail="This will clear and rebuild the knowledge base. "
                   "Pass ?confirm=true to proceed.",
        )

    before = get_document_count()
    logger.info("Starting knowledge base re-index. %s chunk(s) currently indexed.", before)

    try:
        clear_database()
    except Exception:
        logger.exception("Re-index failed while clearing the database. No changes made.")
        raise HTTPException(
            status_code=500,
            detail="Re-index failed before any changes were made. Knowledge base is unchanged.",
        )

    try:
        indexed_chunks = ingest_all_pdfs()
    except Exception:
        after = get_document_count()
        logger.exception(
            "Re-index failed during ingestion. Database was cleared and now has %s chunk(s).",
            after,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Re-index failed during ingestion. The knowledge base was cleared "
                f"and now contains {after} chunk(s) — call /admin/reindex again to retry."
            ),
        )

    after = get_document_count()

    if after == 0:
        logger.warning(
            "Re-index completed but produced 0 chunks (previously had %s). "
            "Check storage/uploads/pdfs for valid PDFs.",
            before,
        )
        return {
            "success": False,
            "previous_chunks": before,
            "indexed_chunks": indexed_chunks,
            "current_chunks": after,
            "message": (
                "Re-index ran but the knowledge base is now empty. "
                "Check that storage/uploads/pdfs contains valid PDFs."
            ),
        }

    logger.info("Re-index completed successfully. %s chunk(s) indexed.", after)

    return {
        "success": True,
        "previous_chunks": before,
        "indexed_chunks": indexed_chunks,
        "current_chunks": after,
        "message": "Knowledge base re-indexed successfully.",
    }