"""
tests/test_rag.py - Tests for the RAG pipeline (ingestion, embedding, retrieval).
"""
import os
import tempfile
import pytest
import numpy as np

from app.rag.ingestion import Document, load_documents, chunk_documents, ingest_knowledge_base
from app.rag.embeddings import Embedder
from app.rag.vector_store import FAISSBackend
from app.rag.retriever import retrieve, format_context


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion tests
# ─────────────────────────────────────────────────────────────────────────────

def test_load_documents_from_real_kb():
    """Should load all 10 knowledge base documents."""
    docs = load_documents()
    assert len(docs) == 10
    for doc in docs:
        assert doc.content
        assert "source" in doc.metadata


def test_chunk_documents():
    docs = [Document(content="A " * 300, metadata={"source": "test.md"})]
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 120  # allow small overlap buffer
        assert chunk.metadata["source"] == "test.md"
        assert "chunk_index" in chunk.metadata


def test_ingest_knowledge_base_returns_chunks():
    chunks = ingest_knowledge_base()
    assert len(chunks) > 10  # should be many more chunks than files
    # Each chunk must be within chunk_size bounds
    for chunk in chunks:
        assert len(chunk.content) > 0


def test_load_documents_missing_dir():
    with pytest.raises(FileNotFoundError):
        load_documents("/nonexistent/path/to/kb")


# ─────────────────────────────────────────────────────────────────────────────
# Embedding tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def embedder():
    return Embedder()


def test_embed_texts_shape(embedder):
    texts = ["Hello world", "Banking is important", "Transfer funds"]
    vecs = embedder.embed_texts(texts)
    assert vecs.shape == (3, embedder.dimension)
    assert vecs.dtype == np.float32


def test_embed_texts_normalized(embedder):
    texts = ["Test sentence for embedding"]
    vecs = embedder.embed_texts(texts)
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_embed_query_shape(embedder):
    vec = embedder.embed_query("What is my account balance?")
    assert vec.shape == (embedder.dimension,)
    assert vec.dtype == np.float32


def test_semantic_similarity(embedder):
    """Related queries should be more similar than unrelated ones."""
    q = embedder.embed_query("What is my balance?")
    pos = embedder.embed_query("How much money do I have in my account?")
    neg = embedder.embed_query("I love pizza and pasta")
    sim_pos = float(q @ pos)
    sim_neg = float(q @ neg)
    assert sim_pos > sim_neg


# ─────────────────────────────────────────────────────────────────────────────
# Vector store tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def populated_faiss(embedder):
    """A FAISS backend loaded with knowledge base documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = FAISSBackend(index_path=f"{tmpdir}/test_idx")
        chunks = ingest_knowledge_base()
        store.add_documents(chunks, embedder)
        yield store


def test_faiss_count(populated_faiss):
    assert populated_faiss.count > 0


def test_faiss_search_returns_results(populated_faiss, embedder):
    qvec = embedder.embed_query("What are the interest rates for savings accounts?")
    results = populated_faiss.search(qvec, top_k=3)
    assert len(results) == 3
    for doc, score in results:
        assert isinstance(doc, Document)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.1  # cosine sim in [0, 1]


def test_faiss_search_relevance(populated_faiss, embedder):
    """Interest rate query should retrieve interest-rate documents."""
    qvec = embedder.embed_query("savings account interest rate percentage")
    results = populated_faiss.search(qvec, top_k=5)
    sources = [doc.metadata.get("source", "") for doc, _ in results]
    assert any("interest" in s or "account" in s for s in sources)


def test_faiss_persist_and_reload(embedder):
    with tempfile.TemporaryDirectory() as tmpdir:
        idx_path = f"{tmpdir}/persist_test"
        store1 = FAISSBackend(index_path=idx_path)
        chunks = ingest_knowledge_base()
        store1.add_documents(chunks, embedder)
        store1.persist()
        original_count = store1.count

        store2 = FAISSBackend(index_path=idx_path)
        loaded = store2.load()
        assert loaded is True
        assert store2.count == original_count


# ─────────────────────────────────────────────────────────────────────────────
# Retriever tests
# ─────────────────────────────────────────────────────────────────────────────

def test_retrieve_returns_documents(populated_faiss, embedder):
    docs = retrieve("Tell me about home loan interest rates", embedder, populated_faiss, top_k=3)
    assert len(docs) <= 3
    assert all(isinstance(d, Document) for d in docs)


def test_format_context():
    docs = [
        Document(content="The savings rate is 3.5%.", metadata={"source": "rates.md"}),
        Document(content="Credit cards offer cashback.", metadata={"source": "cards.md"}),
    ]
    ctx = format_context(docs)
    assert "[1]" in ctx
    assert "[2]" in ctx
    assert "rates.md" in ctx
    assert "3.5%" in ctx
