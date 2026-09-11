"""
app/rag/vector_store.py - Pluggable vector store (FAISS default, Chroma optional).
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

import numpy as np

from app.config import get_settings
from app.rag.embeddings import Embedder
from app.rag.ingestion import Document

settings = get_settings()


class VectorStoreBackend(ABC):
    @abstractmethod
    def add_documents(self, docs: List[Document], embedder: Embedder) -> None: ...

    @abstractmethod
    def search(self, query_vec: np.ndarray, top_k: int) -> List[Tuple[Document, float]]: ...

    @abstractmethod
    def persist(self) -> None: ...

    @abstractmethod
    def load(self) -> bool: ...

    @property
    @abstractmethod
    def count(self) -> int: ...


class FAISSBackend(VectorStoreBackend):
    """
    In-memory FAISS index with JSON-persisted document metadata.
    Index type: IndexFlatIP (inner product on normalised vectors == cosine sim).
    """

    def __init__(self, index_path: str | None = None):
        import faiss
        self._faiss = faiss
        self._index_path = Path(index_path or settings.faiss_index_path)
        self._index = None
        self._docs: List[Document] = []
        self._dim: int = 0

    def _ensure_index(self, dim: int) -> None:
        if self._index is None:
            self._index = self._faiss.IndexFlatIP(dim)
            self._dim = dim

    def add_documents(self, docs: List[Document], embedder: Embedder) -> None:
        texts = [d.content for d in docs]
        vecs = embedder.embed_texts(texts)
        self._ensure_index(vecs.shape[1])
        self._index.add(vecs)
        self._docs.extend(docs)

    def search(self, query_vec: np.ndarray, top_k: int) -> List[Tuple[Document, float]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        q = query_vec.reshape(1, -1).astype(np.float32)
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self._docs[idx], float(score)))
        return results

    def persist(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self._index, str(self._index_path) + ".bin")
        meta_path = str(self._index_path) + "_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                [{"content": d.content, "metadata": d.metadata} for d in self._docs],
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[FAISS] Saved index ({self._index.ntotal} vectors) to {self._index_path}")

    def load(self) -> bool:
        idx_file = str(self._index_path) + ".bin"
        meta_file = str(self._index_path) + "_meta.json"
        if not os.path.exists(idx_file) or not os.path.exists(meta_file):
            return False
        self._index = self._faiss.read_index(idx_file)
        with open(meta_file, encoding="utf-8") as f:
            raw = json.load(f)
        self._docs = [Document(content=r["content"], metadata=r["metadata"]) for r in raw]
        print(f"[FAISS] Loaded index ({self._index.ntotal} vectors)")
        return True

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index else 0


class ChromaBackend(VectorStoreBackend):
    """Persistent ChromaDB collection with our own embedder."""

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ):
        import chromadb
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._collection_name = collection_name or settings.chroma_collection
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, docs: List[Document], embedder: Embedder) -> None:
        texts = [d.content for d in docs]
        vecs = embedder.embed_texts(texts).tolist()
        ids = [
            f"{d.metadata.get('source', 'doc')}_{d.metadata.get('chunk_index', i)}"
            for i, d in enumerate(docs)
        ]
        self._collection.add(
            ids=ids,
            embeddings=vecs,
            documents=texts,
            metadatas=[d.metadata for d in docs],
        )
        print(f"[Chroma] Added {len(docs)} documents to collection '{self._collection_name}'")

    def search(self, query_vec: np.ndarray, top_k: int) -> List[Tuple[Document, float]]:
        if self._collection.count() == 0:
            return []
        results = self._collection.query(
            query_embeddings=[query_vec.tolist()],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1.0 - dist
            output.append((Document(content=text, metadata=meta), score))
        return output

    def persist(self) -> None:
        print(f"[Chroma] Collection '{self._collection_name}' persisted at '{self._persist_dir}'")

    def load(self) -> bool:
        count = self._collection.count()
        if count > 0:
            print(f"[Chroma] Loaded existing collection ({count} documents)")
            return True
        return False

    @property
    def count(self) -> int:
        return self._collection.count()


def get_vector_store(embedder: Embedder | None = None) -> VectorStoreBackend:
    """Returns a VectorStoreBackend chosen by VECTOR_STORE_BACKEND env var."""
    backend = settings.vector_store_backend.lower()
    if backend == "chroma":
        store = ChromaBackend()
    else:
        store = FAISSBackend()
    store.load()
    return store
