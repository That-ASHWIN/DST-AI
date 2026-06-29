"""
vector_store.py
Wrapper around ChromaDB for storing and retrieving document chunk embeddings.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any

import chromadb

from backend.config import VECTOR_DB_DIR, TOP_K_RESULTS

logger = logging.getLogger(__name__)

COLLECTION_NAME = "cims_knowledge_base"

# Persistent ChromaDB client
client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

# Single collection for the project
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def add_documents(
    chunks: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """
    Store chunks + embeddings into ChromaDB.

    Args:
        chunks: List of text chunks.
        embeddings: List of embedding vectors, same length/order as chunks.
        metadatas: Optional list of metadata dicts (e.g. {"source": "file.pdf",
                    "page": 3}), same length/order as chunks.

    Returns:
        List of generated IDs for the inserted chunks.
    """
    if not chunks or not embeddings:
        logger.warning("add_documents called with empty chunks/embeddings. Skipping.")
        return []

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
            "must be the same length."
        )

    if metadatas is not None and len(metadatas) != len(chunks):
        raise ValueError(
            f"metadatas ({len(metadatas)}) must match chunks length ({len(chunks)})."
        )

    # UUID-based ids — avoids collisions/overwrites across repeated ingestion runs.
    ids = [str(uuid.uuid4()) for _ in chunks]

    add_kwargs: Dict[str, Any] = {
        "ids": ids,
        "documents": chunks,
        "embeddings": embeddings,
    }
    if metadatas is not None:
        add_kwargs["metadatas"] = metadatas

    collection.add(**add_kwargs)
    logger.info(f"Added {len(chunks)} chunks to collection '{COLLECTION_NAME}'.")
    return ids


def search(query_embedding: List[float], top_k: int = TOP_K_RESULTS) -> Dict[str, Any]:
    """
    Search for the most similar chunks to a query embedding.

    Args:
        query_embedding: Embedding vector of the user query.
        top_k: Number of results to return (defaults to config.TOP_K_RESULTS).

    Returns:
        ChromaDB query result dict (documents, distances, metadatas, ids).
    """
    if not query_embedding:
        raise ValueError("query_embedding cannot be empty.")

    count = collection.count()
    if count == 0:
        logger.warning("Search called but collection is empty.")
        return {"documents": [[]], "distances": [[]], "metadatas": [[]], "ids": [[]]}

    # Don't ask ChromaDB for more results than exist in the collection.
    effective_top_k = min(top_k, count)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_top_k,
    )
    return results


def clear_database() -> None:
    """
    Clears all stored vectors by deleting and recreating the collection.
    Rebinds the module-level `collection` reference so subsequent calls
    to add_documents()/search() use the fresh, empty collection.
    """
    global collection

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception as e:
        logger.warning(f"Could not delete collection '{COLLECTION_NAME}': {e}")

    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    logger.info(f"Collection '{COLLECTION_NAME}' cleared and recreated.")


def get_document_count() -> int:
    """
    Returns the number of chunks currently stored in the collection.
    Useful for health checks / debugging.
    """
    return collection.count()