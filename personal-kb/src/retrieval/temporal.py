from datetime import datetime
from typing import List, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, ScoredPoint

from models.query import ParsedQuery, QueryType
from temporal.parser import parse_temporal_query
from temporal.filters import build_qdrant_filter
from temporal.resolver import TemporalResolver
from .semantic import SemanticRetriever


class TemporalRetriever:
    """
    Combines semantic search with Qdrant server-side temporal filtering.
    Handles temporal range constraints, current vs. historical knowledge state,
    and multi-interval comparison decomposition.
    """

    def __init__(
        self,
        semantic_retriever: Optional[SemanticRetriever] = None,
        resolver: Optional[TemporalResolver] = None,
    ):
        self.semantic_retriever = semantic_retriever or SemanticRetriever()
        self.resolver = resolver or TemporalResolver()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        reference_date: Optional[datetime] = None,
    ) -> Tuple[List[ScoredPoint], ParsedQuery, Optional[Filter]]:
        parsed_query = self.resolver.resolve_query(query, reference_date=reference_date)

        # Handle comparison queries
        if parsed_query.query_type == QueryType.COMPARISON:
            ranges = self.resolver.decompose_comparison(query, reference_date=reference_date)
            if ranges:
                # Multi-range retrieval: query points for each period and combine
                all_points: List[ScoredPoint] = []
                seen_ids = set()
                for r in ranges:
                    sub_pq = ParsedQuery(
                        original_query=query,
                        semantic_query=parsed_query.semantic_query,
                        query_type=QueryType.TEMPORAL,
                        temporal_range=r,
                    )
                    sub_filter = build_qdrant_filter(sub_pq)
                    pts = self.semantic_retriever.search(
                        query_text=sub_pq.semantic_query,
                        query_filter=sub_filter,
                        top_k=top_k,
                    )
                    for p in pts:
                        if p.id not in seen_ids:
                            seen_ids.add(p.id)
                            all_points.append(p)
                all_points.sort(key=lambda pt: pt.payload.get("event_at") or "")
                return all_points, parsed_query, None
            else:
                # Unbounded comparison/timeline query (e.g. "When did my database decision change?")
                # Retrieve relevant decisions
                points = self.semantic_retriever.search(
                    query_text=parsed_query.semantic_query,
                    query_filter=None,
                    top_k=top_k or 10,
                )
                dated_pts = [p for p in points if p.payload.get("event_at")]
                if dated_pts:
                    dated_pts.sort(key=lambda pt: pt.payload.get("event_at"))
                    return dated_pts, parsed_query, None
                else:
                    return points, parsed_query, None

        # Standard query flow
        qdrant_filter = build_qdrant_filter(parsed_query)
        points = self.semantic_retriever.search(
            query_text=parsed_query.semantic_query,
            query_filter=qdrant_filter,
            top_k=top_k,
        )

        # For historical queries, ensure older items are preserved
        if parsed_query.query_type == QueryType.HISTORICAL:
            # Sort by event_at descending or ascending as appropriate
            def sort_key(pt):
                return pt.payload.get("event_at") or ""
            points.sort(key=sort_key, reverse=True)

        return points, parsed_query, qdrant_filter
