"""
Embedding utilities.

Two backends are supported (selected via settings.EMBEDDING_BACKEND):

  * "neural" — sentence-transformers (needs PyTorch). Best quality. Used for
    local dev and any host with enough memory.
  * "lite"   — a torch-free hashing embedding (pure NumPy). Tiny memory and
    instant startup, so the app deploys on free hosting tiers. Lower quality
    but fully functional (skill-overlap scoring is unaffected).
  * "auto"   — use neural if sentence-transformers is importable, else lite.

Both backends produce L2-normalized, fixed-length vectors in a *consistent*
space, so vectors stored at different times remain comparable via cosine.
Embeddings are serialized to/from JSON for portable storage on SQLite/Postgres.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from typing import List

import numpy as np

from app.core.config import settings

# Dimension used by the lite (hashing) backend.
_LITE_DIM = 256


@lru_cache(maxsize=1)
def _resolve_backend() -> str:
    """Decide which embedding backend to use, honoring the 'auto' setting."""
    choice = (settings.EMBEDDING_BACKEND or "auto").lower()
    if choice in ("neural", "lite"):
        return choice
    # auto: prefer neural if the heavy dependency is available.
    try:
        import sentence_transformers  # noqa: F401

        return "neural"
    except Exception:
        return "lite"


@lru_cache(maxsize=1)
def _get_model():
    """Lazily load and cache the sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL)


def _lite_embed(text: str, dim: int = _LITE_DIM) -> List[float]:
    """
    Torch-free embedding via the signed hashing trick.

    Each token is hashed to a bucket with a deterministic +/- sign, counts are
    accumulated, then the vector is L2-normalized. No training or model load,
    so it is instant and uses almost no memory.
    """
    vec = np.zeros(dim, dtype=float)
    for tok in re.findall(r"[a-z0-9]+", (text or "").lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


def embed_text(text: str) -> List[float]:
    """Return a single embedding vector for the given text."""
    if _resolve_backend() == "neural":
        model = _get_model()
        vector = model.encode(text or "", normalize_embeddings=True)
        return vector.tolist()
    return _lite_embed(text)


def active_backend() -> str:
    """Expose the resolved backend (handy for the /health endpoint)."""
    return _resolve_backend()


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
