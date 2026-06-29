"""
text_loader.py
Loads the local knowledge base, chunks it,
creates embeddings, and stores them in ChromaDB.
"""

import logging
from pathlib import Path

from backend.config import DATA_DIR
from backend.ingestion.chunker import chunk_by_sections
from backend.utils.embeddings import get_embeddings
from backend.storage.vector_db import (
    add_documents,
    clear_database,
)

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = DATA_DIR / "knowledge_base.txt"


def load_knowledge_base() -> int:
    """
    Loads the local knowledge base into ChromaDB.

    Safety ordering: the new chunks are embedded BEFORE the old collection
    is cleared. This way, if embedding or chunking fails, the existing
    (old) knowledge base in ChromaDB is left untouched instead of being
    wiped with nothing to replace it.

    Returns:
        Number of chunks inserted.
    """
    if not KNOWLEDGE_FILE.exists():
        raise FileNotFoundError(f"Knowledge base not found: {KNOWLEDGE_FILE}")

    logger.info("Loading knowledge base...")
    text = KNOWLEDGE_FILE.read_text(encoding="utf-8")

    if not text.strip():
        logger.warning(f"Knowledge base file is empty: {KNOWLEDGE_FILE}")
        return 0

    chunks = chunk_by_sections(text)
    if not chunks:
        logger.warning("No chunks generated from knowledge base text.")
        return 0

    # Do the expensive/fallible work (embedding) FIRST, while the old
    # data in ChromaDB is still intact as a fallback.
    embeddings = get_embeddings(chunks, show_progress=True)

    metadatas = [
        {"source": "knowledge_base.txt", "chunk": i + 1}
        for i in range(len(chunks))
    ]

    # Only clear the old collection once we have everything ready to
    # replace it with. If add_documents() itself fails after this point,
    # that's a ChromaDB-level issue we can't fully protect against without
    # transactional support — but we've at least eliminated the most
    # common failure window (chunking/embedding errors).
    clear_database()

    try:
        add_documents(chunks=chunks, embeddings=embeddings, metadatas=metadatas)
    except Exception:
        logger.exception(
            "Failed to add new documents after clearing the database. "
            "The knowledge base is now EMPTY — re-run this script to fix."
        )
        raise

    logger.info(f"Knowledge base indexed successfully. ({len(chunks)} chunks)")
    return len(chunks)


if __name__ == "__main__":
    try:
        inserted = load_knowledge_base()
        print(f"\nIndexed {inserted} chunks successfully.")
    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        logger.exception("Knowledge base loading failed.")
        print(f"\nError: failed to load knowledge base ({e}). Check logs for details.")