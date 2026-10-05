from datetime import datetime, timezone
from typing import List, Optional, Tuple
from models.query import ParsedQuery, QueryType, TemporalRange, TemporalType
from .parser import parse_temporal_query, get_month_range, MONTH_MAP, MONTH_NAMES
import re


class TemporalResolver:
    """
    Resolves temporal intents, decomposes multi-period queries (e.g., comparisons),
    and coordinates between query understanding and retrieval filtering.
    """

    def __init__(self, default_reference_date: Optional[datetime] = None):
        self.default_reference_date = default_reference_date or datetime.now(timezone.utc)

    def resolve_query(
        self,
        query: str,
        reference_date: Optional[datetime] = None,
    ) -> ParsedQuery:
        ref_dt = reference_date or self.default_reference_date
        return parse_temporal_query(query, reference_date=ref_dt)

    def decompose_comparison(
        self,
        query: str,
        reference_date: Optional[datetime] = None,
    ) -> List[TemporalRange]:
        """
        Decompose a comparison query such as 'What changed between March and August?'
        into separate temporal windows for multi-stage retrieval.
        """
        ref_dt = reference_date or self.default_reference_date
        lower_query = query.lower()

        # Find all mentioned months
        found_months = []
        for name in MONTH_NAMES:
            match = re.search(rf"\b{name}\b", lower_query)
            if match:
                found_months.append((match.start(), name))
        
        # Sort by occurrence in query
        found_months.sort(key=lambda x: x[0])

        ranges: List[TemporalRange] = []
        for _, m_name in found_months:
            m_num = MONTH_MAP[m_name]
            start_dt, end_dt = get_month_range(ref_dt.year, m_num)
            ranges.append(
                TemporalRange(
                    start_date=start_dt,
                    end_date=end_dt,
                    temporal_type=TemporalType.EVENT_TIME,
                    description=f"{m_name.capitalize()} {ref_dt.year}",
                )
            )

        return ranges
