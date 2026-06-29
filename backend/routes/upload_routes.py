import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import ALLOWED_FILE_TYPES, MAX_UPLOAD_SIZE, UPLOAD_DIR
from backend.ingestion.pdf_loader import ingest_pdf

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


@router.post("/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF and automatically index it into ChromaDB.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(ALLOWED_FILE_TYPES)} files are allowed.",
        )

    # Use a UUID-based filename instead of the user-supplied one. This avoids
    # path traversal (e.g. "../../etc/passwd.pdf"), filename collisions
    # between different uploads, and unsafe characters in the original name.
    safe_filename = f"{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_DIR / safe_filename

    # Read once into memory and enforce the size limit before writing
    # anything to disk — this avoids partially-written large files from
    # ever landing on disk.
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
        )
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        save_path.write_bytes(contents)
    except OSError as e:
        logger.exception(f"Failed to save uploaded file {safe_filename!r}.")
        raise HTTPException(status_code=500, detail="Could not save the uploaded file.") from e

    try:
        chunks = ingest_pdf(save_path)
    except Exception as e:
        logger.exception(f"Failed to ingest PDF {safe_filename!r} (original name: {file.filename!r}).")
        # Clean up the saved file if indexing failed, so we don't accumulate
        # orphaned PDFs that were never successfully indexed.
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to process and index the PDF.") from e

    logger.info(f"Indexed {chunks} chunks from uploaded file (original name: {file.filename!r}).")

    return {
        "success": True,
        "filename": file.filename,
        "chunks_indexed": chunks,
        "message": "PDF uploaded and indexed successfully.",
    }