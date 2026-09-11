"""
app/rag/retriever.py - Retrieve top-k relevant document chunks for a query.
"""
from typing import List

from app.config import get_settings
from app.rag.embeddings import Embedder
from app.rag.ingestion import Document
from app.rag.vector_store import VectorStoreBackend

settings = get_settings()


def retrieve(
    query: str,
    embedder: Embedder,
    vector_store: VectorStoreBackend,
    top_k: int | None = None,
) -> List[Document]:
    """
    Embed query, search the vector store, return the top-k Document chunks
    sorted by descending similarity score.
    """
    k = top_k or settings.top_k
    query_vec = embedder.embed_query(query)
    results = vector_store.search(query_vec, top_k=k)
    results.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _score in results]


def format_context(docs: List[Document], max_chars: int = 3000) -> str:
    """
    Format retrieved documents into a single context string for the LLM prompt.
    Truncates total context to max_chars to stay within token limits.
    """
    sections = []
    total = 0
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        snippet = f"[{i}] (source: {source})\n{doc.content.strip()}"
        if total + len(snippet) > max_chars:
            break
        sections.append(snippet)
        total += len(snippet)
    return "\n\n".join(sections)
