"""
app/llm/prompts.py - Prompt templates for the RAG pipeline.
"""
from typing import List
from app.rag.ingestion import Document


BANKING_SYSTEM_PROMPT = """\
You are SecureBank Assistant, a helpful, accurate, and professional AI banking advisor.
You assist customers with questions about their accounts, transactions, products, and policies.

Guidelines:
- Always base your answers on the provided context and account data.
- If the answer is not in the context, say so honestly - do not fabricate information.
- Be concise, clear, and polite.
- Never reveal sensitive information beyond what is explicitly asked.
- If a query involves a potential security concern or fraud, flag it clearly.
"""


def build_rag_prompt(
    query: str,
    docs: List[Document],
    banking_context: str | None = None,
) -> tuple[str, List[dict]]:
    """Build (system_prompt, messages) for a RAG-grounded query."""
    rag_sections = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        rag_sections.append(f"[Document {i} - {source}]\n{doc.content.strip()}")
    rag_context = "\n\n".join(rag_sections) if rag_sections else "(No relevant documents found.)"

    user_parts = []
    if banking_context:
        user_parts.append(
            f"--- ACCOUNT DATA ---\n{banking_context}\n--- END ACCOUNT DATA ---"
        )
    user_parts.append(
        f"--- KNOWLEDGE BASE ---\n{rag_context}\n--- END KNOWLEDGE BASE ---"
    )
    user_parts.append(f"Customer question: {query}")

    messages = [{"role": "user", "content": "\n\n".join(user_parts)}]
    return BANKING_SYSTEM_PROMPT, messages


def build_banking_prompt(
    query: str,
    account_data: dict,
) -> tuple[str, List[dict]]:
    """Build a prompt for direct account-data queries (no RAG context needed)."""
    import json
    data_str = json.dumps(account_data, indent=2, default=str)
    user_content = (
        f"--- ACCOUNT DATA ---\n{data_str}\n--- END ACCOUNT DATA ---\n\n"
        f"Customer question: {query}"
    )
    messages = [{"role": "user", "content": user_content}]
    return BANKING_SYSTEM_PROMPT, messages
