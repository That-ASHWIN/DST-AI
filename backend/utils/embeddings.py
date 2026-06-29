from sentence_transformers import SentenceTransformer
from functools import lru_cache
from typing import List
import logging

from backend.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    return model


def get_embedding(text: str) -> List[float]:
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty.")

    model = load_embedding_model()
    embedding = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embedding.tolist()


def get_embeddings(texts: List[str], show_progress: bool = False) -> List[List[float]]:
    if not texts:
        return []

    cleaned = [t for t in texts if t and t.strip()]

    if not cleaned:
        raise ValueError("No valid texts.")

    model = load_embedding_model()

    embeddings = model.encode(
        cleaned,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=32,
        show_progress_bar=show_progress,
    )

    return embeddings.tolist()