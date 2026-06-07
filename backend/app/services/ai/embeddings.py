"""
Embedding utilities.

Uses sentence-transformers (a free, local model) to turn text into vectors.
The model is loaded lazily and cached, so importing this module is cheap and
the (slow) model download/load only happens on first real use.

Embeddings are serialized to/from JSON so they can be stored in a portable
Text column on either SQLite or Postgres.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import List

import numpy as np

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model():
    """Lazily load and cache the sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_text(text: str) -> List[float]:
    """Return a single embedding vector for the given text."""
    model = _get_model()
    vector = model.encode(text or "", normalize_embeddings=True)
    return vector.tolist()


def serialize(vector: List[float]) -> str:
    return json.dumps(vector)


def deserialize(blob: str | None) -> List[float]:
    if not blob:
        return []
    return json.loads(blob)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity in [-1, 1]. Returns 0 for empty/degenerate input."""
    if not a or not b:
        return 0.0
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
