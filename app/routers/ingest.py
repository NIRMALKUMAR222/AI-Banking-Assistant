"""
app/routers/ingest.py - Trigger document ingestion into the vector store.
"""
from fastapi import APIRouter, Depends, Request

from app.middleware.auth import require_api_key
from app.rag.ingestion import ingest_knowledge_base
from app.rag.embeddings import get_embedder
from app.rag.vector_store import get_vector_store

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/")
async def ingest_documents(request: Request):
    """
    Load all documents from the knowledge base directory,
    chunk them, embed them, and add to the vector store.
    """
    embedder = getattr(request.app.state, "embedder", None) or get_embedder()
    vector_store = getattr(request.app.state, "vector_store", None) or get_vector_store(embedder)


    docs = ingest_knowledge_base()
    vector_store.add_documents(docs, embedder)
    vector_store.persist()

    return {
        "status": "ok",
        "documents_ingested": len(docs),
        "vector_store_total": vector_store.count,
        "backend": type(vector_store).__name__,
    }


@router.get("/status")
async def ingest_status(request: Request):
    """Return current vector store statistics."""
    vector_store = getattr(request.app.state, "vector_store", None) or get_vector_store()
    return {
        "backend": type(vector_store).__name__,
        "total_documents": vector_store.count,
    }

