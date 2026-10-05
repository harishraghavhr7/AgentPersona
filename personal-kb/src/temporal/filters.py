from typing import Optional
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    DatetimeRange,
    MatchValue,
)
from models.query import ParsedQuery, TemporalType


def build_qdrant_filter(parsed_query: ParsedQuery) -> Optional[Filter]:
    """
    Translate a ParsedQuery into Qdrant server-side filter conditions.
    Supports DatetimeRange on event_at/valid_from, status matching, and source filters.
    """
    conditions = []

    # 1. Temporal Range Filter
    if parsed_query.temporal_range:
        tr = parsed_query.temporal_range

        # Date range condition (event_at or valid_from)
        target_field = "event_at" if tr.temporal_type == TemporalType.EVENT_TIME else "valid_from"
        
        if tr.start_date is not None or tr.end_date is not None:
            dt_range = DatetimeRange(
                gte=tr.start_date,
                lte=tr.end_date,
            )
            conditions.append(
                FieldCondition(
                    key=target_field,
                    range=dt_range,
                )
            )

        # Status condition (e.g., "active", "superseded")
        if tr.target_status:
            conditions.append(
                FieldCondition(
                    key="status",
                    match=MatchValue(value=tr.target_status),
                )
            )

    # 2. Source type filter if specified
    if parsed_query.target_source_type:
        conditions.append(
            FieldCondition(
                key="source_type",
                match=MatchValue(value=parsed_query.target_source_type),
            )
        )

    # 3. Document ID filter if specified
    if parsed_query.target_document_id:
        conditions.append(
            FieldCondition(
                key="document_id",
                match=MatchValue(value=parsed_query.target_document_id),
            )
        )

    if not conditions:
        return None

    return Filter(must=conditions)
