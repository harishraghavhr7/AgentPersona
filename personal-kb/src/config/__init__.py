from .settings import Settings, get_settings

_settings = get_settings()

OLLAMA_BASE_URL = _settings.ollama_base_url
LLM_MODEL = _settings.llm_model
EMBEDDING_MODEL = _settings.embedding_model
QDRANT_URL = _settings.qdrant_url
QDRANT_COLLECTION = _settings.qdrant_collection
DATA_DIR = str(_settings.data_dir)
CHUNK_SIZE = _settings.chunk_size
CHUNK_OVERLAP = _settings.chunk_overlap
TOP_K = _settings.top_k
RERANK_TOP_K = _settings.rerank_top_k
LOG_LEVEL = _settings.log_level

__all__ = [
    "Settings",
    "get_settings",
    "OLLAMA_BASE_URL",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "QDRANT_URL",
    "QDRANT_COLLECTION",
    "DATA_DIR",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "TOP_K",
    "RERANK_TOP_K",
    "LOG_LEVEL",
]
