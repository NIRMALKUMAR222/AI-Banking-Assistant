"""
app/llm/grok_client.py - Grok (xAI) LLM client using the OpenAI-compatible API.
"""
from __future__ import annotations

import json
import re
from typing import List

from openai import OpenAI

from app.config import get_settings

settings = get_settings()


class GrokClient:
    """
    OpenAI-compatible client for Groq and Grok (xAI).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ):
        self.api_key = api_key or settings.active_llm_api_key
        self.base_url = base_url or settings.active_llm_base_url
        self.model = model or settings.active_llm_model
        self.provider = provider or settings.active_llm_provider

        # OpenAI client requires a non-empty string api_key
        client_key = self.api_key if (self.api_key and "placeholder" not in self.api_key.lower()) else "dummy-placeholder-key"
        self._client = OpenAI(
            api_key=client_key,
            base_url=self.base_url,
        )


    def chat(
        self,
        messages: List[dict],
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def chat_stub(
        self,
        messages: List[dict],
        system: str | None = None,
        **_kwargs,
    ) -> str:
        """
        Offline stub: generates a contextual response by parsing the banking data
        injected into the prompt. Does NOT echo raw JSON or internal prompt text.
        """
        # ── 1. Extract the real user question ───────────────────────────────
        # The prompt builder appends "Customer question: {query}" at the end of
        # the LAST user message. Conversation history is prepended, so we search
        # in reverse to find the most-recent user turn that has the marker.
        user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                content = m.get("content", "")
                cq_match = re.search(r"Customer question:\s*(.+?)$", content, re.DOTALL)
                if cq_match:
                    user_query = cq_match.group(1).strip()
                    break
                if "---" not in content:   # plain message, no injected context
                    user_query = content.strip()
                    break
        if not user_query:
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    cq_match = re.search(r"Customer question:\s*(.+?)$", content, re.DOTALL)
                    if cq_match:
                        user_query = cq_match.group(1).strip()
                        break

        # ── 2. Extract structured banking data from injected context ─────────
        combined  = (system or "") + " ".join(m.get("content", "") for m in messages)
        balance   = _extract_field(combined, "balance")
        avail_bal = _extract_field(combined, "available_balance")
        acc_type  = _extract_field(combined, "account_type")
        status    = _extract_field(combined, "status")
        currency  = _extract_field(combined, "currency", default="USD")
        owner     = _extract_field(combined, "owner_name")
        txns      = _extract_json_list(combined, "recent_transactions")
        card_type = _extract_field(combined, "card_type")
        card_limit = _extract_field(combined, "credit_limit")

        # ── 3. Route to the right answer ─────────────────────────────────────
        q = user_query.lower()

        _TRANSFER_KWS = ["transfer", "send", "wire", "swift", "neft", "rtgs", "imps",
                         "international", "overseas", "abroad", "remit", "remittance", "recipient"]

        # Balance check — guard against transfer queries stealing this branch
        if any(kw in q for kw in ["balance", "how much", "available funds"]) or \
           ("account" in q and not any(kw in q for kw in _TRANSFER_KWS)):
            if balance:
                return (
                    f"Your current {acc_type or 'savings'} account balance is "
                    f"**{currency} {float(balance):,.2f}**.\n\n"
                    f"- **Available balance:** {currency} {float(avail_bal or balance):,.2f}\n"
                    f"- **Account status:** {status or 'Active'}\n\n"
                    f"💡 *Note: GROK_API_KEY is not set — showing demo data. "
                    f"Add your xAI key to `.env` for AI-generated responses.*"
                )
            return "Your account is active. Set `GROK_API_KEY` in `.env` for real AI responses."

        # Transaction history
        if any(kw in q for kw in ["transaction", "history", "statement", "spending", "recent", "payment", "received"]) \
                and not any(kw in q for kw in _TRANSFER_KWS):
            if txns:
                lines = ["Here are your most recent transactions:\n"]
                for t in txns[:5]:
                    amt   = t.get("amount", 0)
                    ttype = t.get("transaction_type", "debit")
                    desc  = t.get("description", "Transaction")
                    date  = str(t.get("date", "")).split("T")[0]
                    sign  = "+" if ttype == "credit" else "-"
                    icon  = "📥" if ttype == "credit" else "📤"
                    lines.append(f"{icon} **{sign}{currency} {abs(float(amt)):,.2f}** — {desc} *({date})*")
                lines.append("\n💡 *Set `GROK_API_KEY` in `.env` for full AI-powered analysis.*")
                return "\n".join(lines)
            return "I can see your transaction history. Set `GROK_API_KEY` in `.env` for detailed analysis."

        # International transfer
        if any(kw in q for kw in ["international", "swift", "overseas", "abroad", "foreign", "remit", "wire"]):
            return (
                "**International Transfers** at SecureBank:\n\n"
                "- **SWIFT transfers:** Supported to 180+ countries — fees from ₹500\n"
                "- **Processing time:** 1–3 business days\n"
                "- **Limits:** Up to USD 25,000/day (higher limits need branch approval)\n"
                "- **Required:** Beneficiary SWIFT/BIC code, IBAN or account number, bank address\n\n"
                "To initiate: go to **Transactions → Transfer Funds → International Transfer**.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for AI-powered transfer guidance.*"
            )

        # Domestic transfer / send money
        if any(kw in q for kw in ["transfer", "send", "neft", "rtgs", "imps", "pay", "recipient"]):
            return (
                "**Domestic Transfers** at SecureBank:\n\n"
                "- **IMPS** — Instant, 24×7, up to ₹5 lakh per transaction\n"
                "- **NEFT** — Settled in batches, Mon–Sat (8 AM – 7 PM)\n"
                "- **RTGS** — Real-time, for amounts ≥ ₹2 lakh\n\n"
                "To send money: go to **Transactions → Transfer Funds**, enter the "
                "recipient's account number and IFSC code, and confirm.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for AI-powered transfer assistance.*"
            )

        # Card inquiry
        if any(kw in q for kw in ["card", "credit card", "debit card", "limit", "reward", "cashback", "pin", "freeze"]):
            if card_type:
                limit_str = f" with a credit limit of {currency} {float(card_limit):,.0f}" if card_limit else ""
                return (
                    f"You have a **{card_type} card**{limit_str}.\n\n"
                    f"Use the **Cards** section to view rewards, block/unblock your card, or reset your PIN.\n\n"
                    f"💡 *Set `GROK_API_KEY` in `.env` for AI-powered card assistance.*"
                )
            return "Visit the **Cards** section to manage your card, view rewards, and set limits."

        # Loan inquiry
        if any(kw in q for kw in ["loan", "mortgage", "emi", "borrow", "installment", "repayment"]):
            return (
                "SecureBank loan offerings:\n\n"
                "| Type | Rate | Max Tenure |\n"
                "|---|---|---|\n"
                "| 🏠 Home Loan | 8.5% p.a. | 30 years |\n"
                "| 💼 Personal Loan | 12% p.a. | 5 years |\n"
                "| 🚗 Auto Loan | 9.5% p.a. | 7 years |\n\n"
                "Visit **Loan Products** to check eligibility and apply.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for personalised loan recommendations.*"
            )

        # Interest rates (savings/FD)
        if any(kw in q for kw in ["interest rate", "fd", "fixed deposit", "savings rate"]):
            return (
                "**SecureBank Interest Rates:**\n\n"
                "- **Savings Account:** 3.5% p.a.\n"
                "- **Fixed Deposit (1 year):** 6.5% p.a.\n"
                "- **Fixed Deposit (3+ years):** 7.0% p.a.\n"
                "- **Senior Citizen FD:** +0.5% additional\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for personalised rate comparisons.*"
            )

        # KYC / compliance
        if any(kw in q for kw in ["kyc", "document", "verify", "identity", "aml", "compliance"]):
            return (
                "**KYC Documents Required:**\n\n"
                "- **Identity proof:** Passport, Aadhaar, PAN card, or Driver's licence\n"
                "- **Address proof:** Utility bill, bank statement (≤3 months), or rental agreement\n"
                "- **Income proof:** Salary slips or ITR (for loan applications)\n\n"
                "Upload documents via the Mobile App or visit any SecureBank branch.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for AI-powered KYC guidance.*"
            )

        # Fraud / security
        if any(kw in q for kw in ["fraud", "unauthorized", "suspicious", "stolen", "scam", "hack", "dispute"]):
            return (
                "🚨 **Suspected fraud? Act immediately:**\n\n"
                "1. **Call** 1800-SECURE-1 (24/7 fraud hotline)\n"
                "2. **Block your card** from the Cards section\n"
                "3. **File a dispute** at any SecureBank branch\n\n"
                "SecureBank provides zero-liability protection for unauthorised transactions "
                "reported within 24 hours.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for AI-powered fraud analysis.*"
            )

        # Cheque book
        if any(kw in q for kw in ["cheque", "check book", "chequebook"]):
            return (
                "To request a **cheque book**, use the **Cheque Book** section in the sidebar.\n\n"
                "Standard delivery takes 5–7 business days. Express delivery (1–2 days) is available "
                "for an additional fee.\n\n"
                "💡 *Set `GROK_API_KEY` in `.env` for AI-powered banking assistance.*"
            )

        # Generic fallback
        q_preview = user_query[:80] + ("..." if len(user_query) > 80 else "")
        return (
            f"Thank you for your question: *\"{q_preview}\"*\n\n"
            "I'm running in **offline demo mode**. I can show you real account data in the "
            "Balance, Transactions, and Cards sections.\n\n"
            "To enable full AI-powered chat, add your xAI Grok API key to `.env`:\n"
            "```\nGROK_API_KEY=xai-your-key-here\n```"
        )


# ---------------------------------------------------------------------------
# Helpers to extract structured data from the prompt context string
# ---------------------------------------------------------------------------

def _extract_json_block(text: str, key: str) -> dict | None:
    """Try to find and parse a JSON object associated with *key* in *text*."""
    pattern = rf'"{re.escape(key)}"\s*:\s*(\{{[^}}]+\}})'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None


def _extract_json_list(text: str, key: str) -> list:
    """Try to find and parse a JSON array associated with *key* in *text*."""
    pattern = rf'"{re.escape(key)}"\s*:\s*(\[[^\]]*\])'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Fall back to trying to find individual objects in the surrounding text
    try:
        objs = re.findall(r'\{[^{}]+\}', text)
        result = []
        for o in objs:
            try:
                parsed = json.loads(o)
                if "amount" in parsed or "transaction_id" in parsed:
                    result.append(parsed)
            except Exception:
                pass
        return result[:10]
    except Exception:
        return []


def _extract_field(text: str, field: str, default: str | None = None) -> str | None:
    """Extract a scalar JSON field value from embedded context text."""
    pattern = rf'"{re.escape(field)}"\s*:\s*(["\d][^,\n\]}}]*)'
    match = re.search(pattern, text)
    if match:
        raw = match.group(1).strip().strip('"').strip("'")
        return raw or default
    return default


_client: GrokClient | None = None


def get_grok_client() -> GrokClient:
    """Singleton Grok/Groq LLM Client."""
    global _client
    if _client is None:
        _client = GrokClient()
    return _client


# Convenience aliases for Groq
GroqClient = GrokClient
get_groq_client = get_grok_client
LLMClient = GrokClient
get_llm_client = get_grok_client