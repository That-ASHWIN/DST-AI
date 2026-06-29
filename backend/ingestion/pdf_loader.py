"""
pdf_loader.py
Loads PDF files, extracts text, chunks it,
creates embeddings, and stores them in ChromaDB.
"""
import logging
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.config import UPLOAD_DIR
from backend.ingestion.chunker import chunk_text
from backend.utils.embeddings import get_embeddings
from backend.storage.vector_db import add_documents

logger = logging.getLogger(__name__)


def extract_pages_from_pdf(pdf_path: Path) -> List[Tuple[int, str]]:
    """
    Extract text from a PDF, page by page.

    Returns:
        List of (page_number, page_text) tuples for pages with
        non-empty extracted text. page_number is 1-indexed.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as e:
        raise PdfReadError(f"Could not open {pdf_path.name}: {e}") from e

    if reader.is_encrypted:
        # Try an empty password first (common for "owner-locked" PDFs);
        # if that fails, we can't safely proceed.
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError(f"{pdf_path.name} is password-protected and cannot be read")

    pages: List[Tuple[int, str]] = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning("Failed to extract page %d from %s: %s", page_num, pdf_path.name, e)
            continue
        if text.strip():
            pages.append((page_num, text))
    return pages


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract full text from a PDF file (all pages joined).
    Kept for backward compatibility with callers that just want raw text.
    """
    return "\n".join(text for _, text in extract_pages_from_pdf(pdf_path))


def ingest_pdf(pdf_path: Path) -> int:
    """
    Ingest a single PDF into ChromaDB.

    Returns:
        Number of chunks inserted.
    """
    logger.info("Ingesting PDF: %s", pdf_path.name)

    try:
        pages = extract_pages_from_pdf(pdf_path)
    except (PdfReadError, ValueError) as e:
        logger.error("Skipping %s: %s", pdf_path.name, e)
        return 0

    if not pages:
        logger.warning("No readable text found in %s", pdf_path.name)
        return 0

    # Chunk per page so each chunk can carry an accurate page number.
    all_chunks: List[str] = []
    all_page_nums: List[int] = []
    for page_num, page_text in pages:
        page_chunks = chunk_text(page_text)
        all_chunks.extend(page_chunks)
        all_page_nums.extend([page_num] * len(page_chunks))

    if not all_chunks:
        logger.warning("No chunks generated for %s", pdf_path.name)
        return 0

    embeddings = get_embeddings(all_chunks, show_progress=True)

    metadatas = [
        {
            "source": pdf_path.name,
            "chunk": i + 1,
            "page": all_page_nums[i],
        }
        for i in range(len(all_chunks))
    ]
    add_documents(
        chunks=all_chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("Indexed %d chunks from %s", len(all_chunks), pdf_path.name)
    return len(all_chunks)


def ingest_all_pdfs() -> int:
    """
    Index all PDFs inside UPLOAD_DIR (case-insensitive .pdf match).

    Returns:
        Total number of chunks inserted.
    """
    pdf_files = sorted(
        {p for p in UPLOAD_DIR.glob("*") if p.suffix.lower() == ".pdf"}
    )
    if not pdf_files:
        logger.warning("No PDF files found.")
        return 0

    total_chunks = 0
    failed: List[str] = []
    for pdf in pdf_files:
        try:
            total_chunks += ingest_pdf(pdf)
        except Exception:
            logger.exception("Failed to process %s", pdf.name)
            failed.append(pdf.name)

    logger.info("Finished indexing PDFs. Total chunks: %d", total_chunks)
    if failed:
        logger.warning("Failed files (%d): %s", len(failed), ", ".join(failed))
    return total_chunks


if __name__ == "__main__":
    inserted = ingest_all_pdfs()
    print(f"\nIndexed {inserted} PDF chunks.")