from typing import Any, List, Optional
import logging
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import TextNode
from llama_index.embeddings.ollama import OllamaEmbedding

from config.settings import get_settings
from storage.qdrant import get_vector_store

logger = logging.getLogger(__name__)


def get_embedding_model() -> Any:
    """
    Returns configured embedding model based on settings.embedding_provider:
    - 'ollama' (default): Local Ollama embedding (e.g. embeddinggemma)
    - 'fastembed': Lightweight serverless CPU embedding (e.g. BAAI/bge-base-en-v1.5)
    - 'openai': OpenAI cloud embedding (e.g. text-embedding-3-small)
    """
    settings = get_settings()
    provider = settings.embedding_provider.lower()

    if provider == "fastembed":
        try:
            from llama_index.embeddings.fastembed import FastEmbedEmbedding
            model_name = settings.embedding_model if settings.embedding_model != "embeddinggemma" else "BAAI/bge-base-en-v1.5"
            logger.info(f"Using FastEmbed embedding model: {model_name}")
            return FastEmbedEmbedding(model_name=model_name)
        except Exception as e:
            logger.warning(f"Could not load FastEmbed ({e}). Falling back to Ollama.")

    elif provider == "openai":
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
            model_name = settings.embedding_model if settings.embedding_model != "embeddinggemma" else "text-embedding-3-small"
            logger.info(f"Using OpenAI embedding model: {model_name}")
            return OpenAIEmbedding(model_name=model_name)
        except Exception as e:
            logger.warning(f"Could not load OpenAI embedding ({e}). Falling back to Ollama.")

    # Default to Ollama
    return OllamaEmbedding(
        model_name=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )


def create_ingestion_pipeline() -> IngestionPipeline:
    """Create an IngestionPipeline with configured embeddings and Qdrant storage."""
    vector_store = get_vector_store()
    embed_model = get_embedding_model()

    # Ensure Settings has the embed model
    Settings.embed_model = embed_model

    return IngestionPipeline(
        transformations=[embed_model],
        vector_store=vector_store,
    )


def run_node_ingestion(nodes: List[TextNode]) -> List[TextNode]:
    """Execute embedding and insertion into Qdrant for a list of TextNodes."""
    if not nodes:
        return []
    pipeline = create_ingestion_pipeline()
    return list(pipeline.run(nodes=nodes))