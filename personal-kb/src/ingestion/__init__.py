from .loaders import load_from_directory, load_single_file
from .parser import parse_document_into_chunks
from .deduplication import ManifestManager
from .pipeline import create_ingestion_pipeline, run_node_ingestion, get_embedding_model
from .service import IngestionService

# Backward-compatibility aliases
load_documents = load_from_directory

__all__ = [
    "load_from_directory",
    "load_single_file",
    "load_documents",
    "parse_document_into_chunks",
    "ManifestManager",
    "create_ingestion_pipeline",
    "run_node_ingestion",
    "get_embedding_model",
    "IngestionService",
]
