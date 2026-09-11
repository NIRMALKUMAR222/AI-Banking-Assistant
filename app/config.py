"""
app/config.py - Application settings loaded from environment / .env
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM (Groq & Grok / xAI) ──────────────────────────────────────────────
    # Groq (https://console.groq.com) — Fast LPU inference
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    groq_base_url: str = "https://api.groq.com/openai/v1"


    # Grok (https://console.x.ai) — xAI API
    grok_api_key: str = "xai-placeholder"
    grok_model: str = "grok-beta"
    grok_base_url: str = "https://api.x.ai/v1"

    # Optional explicit override: "groq" | "grok"
    llm_provider: str | None = None

    @property
    def active_llm_provider(self) -> str:
        """Auto-detect active LLM provider based on set keys or explicit provider."""
        if self.llm_provider:
            return self.llm_provider.lower().strip()
        # If groq_api_key is set and not a placeholder
        if self.groq_api_key and "placeholder" not in self.groq_api_key.lower():
            return "groq"
        # If grok_api_key was used with a Groq key (starts with gsk_)
        if self.grok_api_key and self.grok_api_key.startswith("gsk_"):
            return "groq"
        # If grok_api_key is set and not a placeholder
        if self.grok_api_key and "placeholder" not in self.grok_api_key.lower():
            return "grok"
        return "groq" if self.groq_api_key else "grok"

    @property
    def active_llm_api_key(self) -> str:
        """Resolve the active API key."""
        prov = self.active_llm_provider
        if prov == "groq":
            if self.groq_api_key and "placeholder" not in self.groq_api_key.lower():
                return self.groq_api_key
            if self.grok_api_key and self.grok_api_key.startswith("gsk_"):
                return self.grok_api_key
            return self.groq_api_key or self.grok_api_key or "placeholder"
        return self.grok_api_key or "placeholder"

    @property
    def active_llm_base_url(self) -> str:
        """Resolve the active base URL."""
        return self.groq_base_url if self.active_llm_provider == "groq" else self.grok_base_url

    @property
    def active_llm_model(self) -> str:
        """Resolve the active model ensuring Groq gets a valid Groq model."""
        if self.active_llm_provider == "groq":
            if self.groq_model and not self.groq_model.lower().startswith("grok"):
                return self.groq_model
            if self.grok_model and not self.grok_model.lower().startswith("grok"):
                return self.grok_model
            return "llama-3.3-70b-versatile"
        return self.grok_model


    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Vector Store
    vector_store_backend: str = "faiss"          # "faiss" | "chroma"
    faiss_index_path: str = "./data/faiss_index"
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection: str = "securebank_docs"

    # Retrieval
    top_k: int = 5
    knowledge_base_dir: str = "./data/knowledge_base"

    # Auth — API key (legacy, for service-to-service calls)
    api_key: str = "securebank-dev-key-change-me"

    # Auth — JWT
    jwt_secret_key: str = "CHANGE-ME-use-a-long-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "*"

    # Logging
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()