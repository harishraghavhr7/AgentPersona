from typing import Dict
from qdrant_client.http.models import PayloadSchemaType

PAYLOAD_INDEXES: Dict[str, PayloadSchemaType] = {
    "event_at": PayloadSchemaType.DATETIME,
    "valid_from": PayloadSchemaType.DATETIME,
    "valid_until": PayloadSchemaType.DATETIME,
    "ingested_at": PayloadSchemaType.DATETIME,
    "status": PayloadSchemaType.KEYWORD,
    "document_id": PayloadSchemaType.KEYWORD,
    "source_type": PayloadSchemaType.KEYWORD,
    "topic": PayloadSchemaType.KEYWORD,
    "version": PayloadSchemaType.INTEGER,
}
