"""
tests/test_groq_llm.py — Unit tests for Groq LLM integration and provider auto-detection.
"""
from app.config import Settings
from app.llm.grok_client import GrokClient, GroqClient, get_groq_client, get_grok_client


def test_groq_auto_detection_from_key():
    """A key starting with gsk_ should automatically route to Groq with Groq base URL."""
    s = Settings(
        grok_api_key="gsk_test_key_1234567890",
        _env_file=None,
    )
    assert s.active_llm_provider == "groq"
    assert s.active_llm_base_url == "https://api.groq.com/openai/v1"
    assert s.active_llm_api_key == "gsk_test_key_1234567890"
    assert "grok" not in s.active_llm_model.lower()


def test_groq_explicit_key():
    """Setting groq_api_key should configure Groq."""
    s = Settings(
        groq_api_key="gsk_explicit_groq_key",
        grok_api_key="xai-placeholder",
        _env_file=None,
    )
    assert s.active_llm_provider == "groq"
    assert s.active_llm_base_url == "https://api.groq.com/openai/v1"
    assert s.active_llm_api_key == "gsk_explicit_groq_key"


def test_grok_xai_key():
    """Setting an xai key should configure xAI."""
    s = Settings(
        groq_api_key=None,
        grok_api_key="xai-real-key-12345",
        _env_file=None,
    )
    assert s.active_llm_provider == "grok"
    assert s.active_llm_base_url == "https://api.x.ai/v1"
    assert s.active_llm_api_key == "xai-real-key-12345"


def test_groq_client_aliases():
    """GroqClient and GrokClient should refer to the same class and singleton."""
    assert GroqClient is GrokClient
    client1 = get_groq_client()
    client2 = get_grok_client()
    assert client1 is client2
    assert hasattr(client1, "chat")
    assert hasattr(client1, "chat_stub")