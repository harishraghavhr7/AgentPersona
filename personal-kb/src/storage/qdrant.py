import logging
import os
import urllib.request
import warnings
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from llama_index.vector_stores.qdrant import QdrantVectorStore

from config.settings import get_settings
from .indexes import PAYLOAD_INDEXES

logger = logging.getLogger(__name__)

_client_instance: Optional[QdrantClient] = None
_client_target: Optional[str] = None


def _is_qdrant_server_reachable(url: str, timeout: float = 0.5) -> bool:
    """Check whether a remote Qdrant server is alive and responding."""
    try:
        test_url = url.rstrip("/") + "/readyz"
        with urllib.request.urlopen(test_url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status in (200, 404)
        except Exception:
            return False


def get_qdrant_client(url: Optional[str] = None) -> QdrantClient:
    """
    Returns an initialized QdrantClient.
    Supports Qdrant Cloud (with API Key), remote Docker Qdrant, and local embedded disk fallback.
    """
    global _client_instance, _client_target
    settings = get_settings()
    target_url = url or settings.qdrant_url
    api_key = settings.qdrant_api_key
    target_key = f"{target_url}:{bool(api_key)}"

    if _client_instance is not None and _client_target == target_key:
        return _client_instance

    local_path = str(settings.data_dir.parent / "qdrant_storage")

    # Auto-enforce https:// for Qdrant Cloud endpoints
    if "qdrant.io" in target_url and target_url.startswith("http://"):
        target_url = "https://" + target_url[len("http://"):]

    # 1. Explicit local / embedded configuration
    if target_url.lower() in ("local", "embedded", ""):
        logger.info(f"Using embedded local Qdrant database at: {local_path}")
        _client_instance = QdrantClient(path=local_path)
        _client_target = target_key
        return _client_instance

    # 2. Qdrant Cloud (HTTPS or explicit API key)
    if api_key or target_url.startswith("https://") or "qdrant.io" in target_url:
        logger.info(f"Connecting to Qdrant Cloud at: {target_url}")
        _client_instance = QdrantClient(url=target_url, api_key=api_key)
        _client_target = target_key
        return _client_instance

    # 3. Check if local/remote Qdrant server is active
    if _is_qdrant_server_reachable(target_url):
        logger.info(f"Connected to Qdrant server at: {target_url}")
        _client_instance = QdrantClient(url=target_url, api_key=api_key)
        _client_target = target_key
        return _client_instance

    # 4. Graceful fallback to local disk storage
    logger.warning(
        f"Qdrant server at '{target_url}' is not running/reachable. "
        f"Falling back to embedded local disk storage at '{local_path}'. "
        f"(Start Docker and run 'docker compose up -d' if you prefer the server container.)"
    )
    _client_instance = QdrantClient(path=local_path)
    _client_target = target_key
    return _client_instance


def ensure_collection_and_indexes(
    client: Optional[QdrantClient] = None,
    collection_name: Optional[str] = None,
    vector_size: int = 768,
) -> None:
    """
    Ensure the target Qdrant collection exists and all temporal/metadata payload indexes are created.
    """
    settings = get_settings()
    target_client = client or get_qdrant_client()
    target_coll = collection_name or settings.qdrant_collection

    try:
        # 1. Ensure collection exists
        collections_res = target_client.get_collections()
        existing_collections = [c.name for c in collections_res.collections]

        if target_coll not in existing_collections:
            logger.info(f"Creating Qdrant collection: {target_coll}")
            target_client.create_collection(
                collection_name=target_coll,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

        # 2. Inspect existing indexes and create missing ones
        collection_info = target_client.get_collection(target_coll)
        existing_schema = collection_info.payload_schema or {}

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*Payload indexes have no effect in the local Qdrant.*"
            )
            for field_name, schema_type in PAYLOAD_INDEXES.items():
                if field_name not in existing_schema:
                    try:
                        logger.info(
                            f"Creating payload index for '{field_name}' ({schema_type}) in '{target_coll}'"
                        )
                        target_client.create_payload_index(
                            collection_name=target_coll,
                            field_name=field_name,
                            field_schema=schema_type,
                            wait=True,
                        )
                    except Exception as e:
                        logger.debug(f"Could not create payload index for '{field_name}': {e}")
    except Exception as e:
        detail = ""
        if hasattr(e, "content") and e.content:
            try:
                detail = f" (Server response: {e.content.decode('utf-8', errors='ignore')})"
            except Exception:
                detail = f" (Server response: {e.content})"
        logger.error(f"Error during Qdrant collection/index setup: {e}{detail}")
        raise


def get_vector_store(
    client: Optional[QdrantClient] = None,
    collection_name: Optional[str] = None,
) -> QdrantVectorStore:
    settings = get_settings()
    target_client = client or get_qdrant_client()
    target_coll = collection_name or settings.qdrant_collection

    ensure_collection_and_indexes(target_client, target_coll)

    return QdrantVectorStore(
        client=target_client,
        collection_name=target_coll,
    )
