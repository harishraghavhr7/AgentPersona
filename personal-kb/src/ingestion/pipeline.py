from typing import List, Optional
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import TextNode
from llama_index.embeddings.ollama import OllamaEmbedding

from config.settings import get_settings
from storage.qdrant import get_vector_store


def get_embedding_model() -> OllamaEmbedding:
    settings = get_settings()
    return OllamaEmbedding(
        model_name=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )


def create_ingestion_pipeline() -> IngestionPipeline:
    """Create an IngestionPipeline with Ollama embeddings and Qdrant storage."""
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