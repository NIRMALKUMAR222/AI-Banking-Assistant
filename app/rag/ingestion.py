"""
app/rag/ingestion.py - Load and chunk documents from the knowledge base directory.
"""
import os
from pathlib import Path
from typing import List
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

settings = get_settings()


@dataclass
class Document:
    """A text chunk with metadata."""
    content: str
    metadata: dict = field(default_factory=dict)


def load_documents(directory: str | None = None) -> List[Document]:
    """Load all .txt and .md files from directory."""
    kb_dir = Path(directory or settings.knowledge_base_dir)
    if not kb_dir.exists():
        raise FileNotFoundError(f"Knowledge base directory not found: {kb_dir}")

    docs: List[Document] = []
    for ext in ("*.txt", "*.md"):
        for fp in sorted(kb_dir.glob(ext)):
            text = fp.read_text(encoding="utf-8")
            docs.append(Document(
                content=text,
                metadata={
                    "source": fp.name,
                    "path": str(fp),
                    "file_type": fp.suffix.lstrip("."),
                },
            ))
    return docs


def chunk_documents(
    docs: List[Document],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> List[Document]:
    """Split each document into smaller overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunked: List[Document] = []
    for doc in docs:
        parts = splitter.split_text(doc.content)
        for i, part in enumerate(parts):
            chunked.append(Document(
                content=part,
                metadata={
                    **doc.metadata,
                    "chunk_index": i,
                    "chunk_total": len(parts),
                },
            ))
    return chunked


def ingest_knowledge_base(
    directory: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> List[Document]:
    """Convenience: load + chunk in one call."""
    raw = load_documents(directory)
    return chunk_documents(raw, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
