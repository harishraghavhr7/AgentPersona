import hashlib
from datetime import datetime
from pathlib import Path


def generate_document_id(text: str):

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:16]


def enrich_documents(documents):

    now = datetime.now().isoformat()

    for document in documents:

        document_id = generate_document_id(
            document.text
        )

        file_path = document.metadata.get(
            "file_path",
            "unknown",
        )

        source_type = Path(
            file_path
        ).suffix.lower()

        document.metadata.update({

            "document_id": document_id,

            "source": file_path,

            "source_type": source_type,

            "created_at": now,

            "updated_at": now,

            "valid_from": None,

            "valid_until": None,

            "version": 1,

            "status": "active",

        })

    return documents