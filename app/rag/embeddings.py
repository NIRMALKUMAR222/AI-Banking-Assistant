"""
app/rag/embeddings.py - HuggingFace sentence-transformers embedding wrapper.
"""
from functools import lru_cache
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

settings = get_settings()


class Embedder:
    """Wraps a SentenceTransformer model to produce normalized float32 embeddings."""

    def __init__(self, model_name: str | None = None):
        name = model_name or settings.embedding_model
        print(f"[embeddings] Loading model '{name}' ...")
        self._model = SentenceTransformer(name)
        self.dimension: int = self._model.get_sentence_embedding_dimension()
        print(f"[embeddings] Model loaded. Dimension = {self.dimension}")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of texts.
        Returns shape (n, dim) float32 array, L2-normalised.
        """
        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vecs.astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """
        Embed a single query string.
        Returns shape (dim,) float32 array, L2-normalised.
        """
        return self.embed_texts([text])[0]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Singleton embedder - loaded once per process."""
    return Embedder()
