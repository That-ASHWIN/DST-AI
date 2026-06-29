"""
chunker.py
Splits extracted document text into overlapping chunks for embedding.
Ensures empty/whitespace-only chunks are filtered out at the source,
so no downstream module (embeddings, vector DB) ever has to handle them.
"""

import logging
from typing import List

from backend.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Splits a single block of text into overlapping chunks.

    Args:
        text: Full extracted text (from PDF, scraper, or knowledge base file).
        chunk_size: Max characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        List of clean, non-empty text chunks. Empty or whitespace-only
        chunks are never included.
    """
    if not text or not text.strip():
        logger.warning("chunk_text called with empty input text. Returning [].")
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    text = text.strip()
    chunks: List[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        # --- Boundary validation: only keep non-empty, meaningful chunks ---
        if chunk.strip():
            chunks.append(chunk.strip())

        # Move start forward, accounting for overlap
        start += chunk_size - chunk_overlap

    logger.info(f"Generated {len(chunks)} chunks from input text of length {text_length}.")
    return chunks


def chunk_documents(documents: List[str]) -> List[str]:
    """
    Chunks multiple documents (e.g., multiple PDFs or knowledge base sections)
    and returns a single flat, clean list of chunks.

    Args:
        documents: List of raw text blocks, one per source document.

    Returns:
        Flat list of clean, non-empty chunks across all documents.
    """
    all_chunks: List[str] = []

    for i, doc in enumerate(documents):
        if not doc or not doc.strip():
            logger.warning(f"Document at index {i} is empty. Skipping.")
            continue
        all_chunks.extend(chunk_text(doc))

    logger.info(f"Total chunks generated across {len(documents)} documents: {len(all_chunks)}")
    return all_chunks


def chunk_by_sections(text: str, section_delimiter: str = "[SECTION:") -> List[str]:
    """
    Section-aware chunking for structured knowledge base files
    (like cims_knowledge_base.txt) that use '[SECTION: NAME]' markers.

    Falls back to chunk_text() for any section that is still larger
    than CHUNK_SIZE after splitting.

    Args:
        text: Full knowledge base text containing section markers.
        section_delimiter: The marker that starts a new section.

    Returns:
        List of clean, non-empty chunks, one per section (or sub-chunked
        if a section is too large).
    """
    if not text or not text.strip():
        logger.warning("chunk_by_sections called with empty input text. Returning [].")
        return []

    if section_delimiter not in text:
        # No section markers at all — just do normal chunking
        return chunk_text(text)

    raw_parts = text.split(section_delimiter)
    chunks: List[str] = []

    # raw_parts[0] is the preamble BEFORE the first "[SECTION:" marker
    # (e.g. title/header lines) — it never gets the delimiter re-attached.
    preamble = raw_parts[0].strip()
    if preamble:
        if len(preamble) <= CHUNK_SIZE:
            chunks.append(preamble)
        else:
            chunks.extend(chunk_text(preamble))

    # Every remaining part DID follow a "[SECTION:" marker, so re-attach it.
    for part in raw_parts[1:]:
        part = part.strip()
        if not part:
            continue

        section_text = f"{section_delimiter}{part}"

        if len(section_text) <= CHUNK_SIZE:
            chunks.append(section_text)
        else:
            # Section too large — fall back to standard overlapping chunking
            chunks.extend(chunk_text(section_text))

    logger.info(f"Generated {len(chunks)} section-aware chunks.")
    return chunks