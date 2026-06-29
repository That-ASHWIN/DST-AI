"""
retrieval.py
Retrieves the most relevant knowledge base chunks for a user query
using semantic search over ChromaDB.
"""

import logging
import time
from typing import List, Optional

from backend.config import TOP_K_RESULTS
from backend.utils.embeddings import get_embedding
from backend.storage.vector_db import search

logger = logging.getLogger(__name__)

# ChromaDB returns cosine DISTANCE (lower = more similar), since embeddings
# are normalized. A distance above this is treated as "not relevant enough" —
# tune this based on testing with real CIMS queries.
MAX_RELEVANT_DISTANCE = 2.0

def retrieve_context(
    query: str,
    top_k: int = TOP_K_RESULTS,
    max_distance: Optional[float] = MAX_RELEVANT_DISTANCE,
) -> List[str]:
    """
    Retrieve the most relevant chunks for a user query.

    Args:
        query: User question.
        top_k: Number of chunks to retrieve.
        max_distance: Discard chunks whose distance from the query is above
                       this threshold (i.e. too dissimilar to be useful).
                       Pass None to disable filtering.

    Returns:
        List of retrieved text chunks, ordered most-relevant first.
    """
    if not query or not query.strip():
        logger.warning("retrieve_context called with empty query.")
        return []

    start = time.perf_counter()
    query_embedding = get_embedding(query)
    print(f"Embedding Time: {time.perf_counter()-start:.2f} sec")

    results = search(
        query_embedding=query_embedding,
        top_k=top_k,
    )

    # ChromaDB always returns a list of lists (one list per input query embedding).
    # We only ever send one query embedding at a time, so we read index [0].
    documents = results.get("documents") or [[]]
    distances = results.get("distances") or [[]]

    retrieved_docs = documents[0] if documents else []
    retrieved_distances = distances[0] if distances else []

    if not retrieved_docs:
        logger.info("No relevant context found for query.")
        return []

    if max_distance is None:
        logger.info(f"Retrieved {len(retrieved_docs)} chunks (no distance filter applied).")
        return retrieved_docs

    # Filter out chunks that are too dissimilar to be trustworthy context.
    filtered_chunks = [
        doc
        for doc, dist in zip(retrieved_docs, retrieved_distances)
        if dist <= max_distance
    ]

    dropped = len(retrieved_docs) - len(filtered_chunks)
    if dropped:
        logger.info(f"Dropped {dropped} chunk(s) below relevance threshold ({max_distance}).")

    logger.info(f"Retrieved {len(filtered_chunks)} relevant chunks.")
    return filtered_chunks


def retrieve_context_as_text(
    query: str,
    top_k: int = TOP_K_RESULTS,
    max_distance: Optional[float] = MAX_RELEVANT_DISTANCE,
) -> str:
    """
    Returns retrieved chunks as one formatted string, ready to be inserted
    into the LLM's context window alongside the system prompt.

    Returns an empty string if no relevant chunks were found — the caller
    (e.g. the chat/LLM layer) should treat an empty string as "no context
    available" and respond accordingly (per SYSTEM_PROMPT fallback rule).
    """
    chunks = retrieve_context(query, top_k=top_k, max_distance=max_distance)
    if not chunks:
        return ""
    return "\n\n".join(chunks)