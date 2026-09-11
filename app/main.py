"""
app/main.py - FastAPI application entry point
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging, RequestLoggingMiddleware
from app.routers import chat, ingest, banking, auth as auth_router
from app.rag.vector_store import get_vector_store
from app.rag.embeddings import get_embedder

settings = get_settings()
setup_logging()
logger = logging.getLogger("securebank.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load embedder + vector store so first request is fast."""
    logger.info("Starting SecureBank RAG API", extra={"version": "1.0.0"})
    app.state.embedder = get_embedder()
    app.state.vector_store = get_vector_store(app.state.embedder)
    logger.info(
        "Ready",
        extra={
            "vector_store_backend": settings.vector_store_backend,
            "embedding_model":      settings.embedding_model,
            "llm_model":            settings.grok_model,
        },
    )
    yield
    logger.info("Shutting down SecureBank RAG API")


app = FastAPI(
    title="SecureBank RAG API",
    description="Banking chatbot powered by RAG + Grok LLM",
    version="1.0.0",
    lifespan=lifespan,
    # Hide sensitive routes from public Swagger in production
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters — outermost first) ───────────────────────────
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth_router.router, prefix="/auth",    tags=["Auth"])
app.include_router(chat.router,        prefix="/chat",    tags=["Chat"])
app.include_router(ingest.router,      prefix="/ingest",  tags=["Ingest"])
app.include_router(banking.router,     prefix="/banking", tags=["Banking"])


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "vector_store":    settings.vector_store_backend,
        "embedding_model": settings.embedding_model,
        "llm":             settings.grok_model,
    }