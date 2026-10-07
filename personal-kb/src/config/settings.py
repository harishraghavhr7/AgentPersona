import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
load_dotenv()


class Settings(BaseModel):
    # LLM Fallback Order: Groq -> Gemini -> OpenRouter
    llm_fallback_order: list[str] = Field(
        default_factory=lambda: [
            p.strip().lower()
            for p in os.getenv("LLM_FALLBACK_ORDER", "groq,gemini,openrouter").split(",")
            if p.strip()
        ]
    )

    # Groq (Primary LLM)
    groq_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY")
    )
    groq_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    )
    groq_base_url: str = Field(
        default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    )

    # Gemini (Secondary LLM)
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    gemini_base_url: str = Field(
        default_factory=lambda: os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    )

    # OpenRouter (Tertiary LLM)
    openrouter_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY")
    )
    openrouter_model: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    )
    openrouter_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )

    # Local Ollama (Optional fallback / Local embeddings)
    enable_ollama_fallback: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_OLLAMA_FALLBACK", "false").lower() in ("true", "1", "yes")
    )
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "llama3.2")
    )
    embedding_provider: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
    )
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "embeddinggemma")
    )

    # Qdrant (Supports local container or Qdrant Cloud https://...cloud.qdrant.io)
    qdrant_url: str = Field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333")
    )
    qdrant_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("QDRANT_API_KEY")
    )
    qdrant_collection: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "personal_knowledge")
    )

    # Data / Ingestion
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", "data"))
    )
    chunk_size: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "512"))
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50"))
    )

    # Retrieval
    top_k: int = Field(
        default_factory=lambda: int(os.getenv("TOP_K", "5"))
    )
    rerank_top_k: int = Field(
        default_factory=lambda: int(os.getenv("RERANK_TOP_K", "3"))
    )

    # Observability
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
