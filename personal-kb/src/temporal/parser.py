import calendar
from datetime import datetime, timezone, timedelta
import re
from typing import Optional, Tuple
import dateutil.parser

from models.query import ParsedQuery, QueryType, TemporalRange, TemporalType


MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_MAP = {name: i + 1 for i, name in enumerate(MONTH_NAMES)}

# Regexes for explicit dates
DATE_PATTERNS = [
    # YYYY-MM-DD
    r"\b(\d{4}-\d{2}-\d{2})\b",
    # Month DD, YYYY (e.g., March 15, 2026)
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\b",
    # DD Month YYYY (e.g., 15 March 2026)
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    # Month YYYY (e.g., March 2026)
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
]


def extract_event_date_from_text(text: str) -> Optional[datetime]:
    """
    Extract deterministic event date from text chunk/sentence.
    Never hallucinates or guesses. Returns None if no clear date is found.
    """
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                dt = dateutil.parser.parse(date_str)
                # Ensure UTC timezone
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except Exception:
                continue
    return None


def get_month_range(year: int, month: int) -> Tuple[datetime, datetime]:
    """Return start and end UTC datetime for a specific year and month."""
    _, last_day = calendar.monthrange(year, month)
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def get_year_range(year: int) -> Tuple[datetime, datetime]:
    """Return start and end UTC datetime for a specific year."""
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def parse_temporal_query(
    query: str,
    reference_date: Optional[datetime] = None,
) -> ParsedQuery:
    """
    Parse a user query deterministically to extract semantic intent,
    temporal bounds, and knowledge state targets.
    """
    ref_dt = reference_date or datetime.now(timezone.utc)
    lower_query = query.lower()

    temporal_range: Optional[TemporalRange] = None
    query_type = QueryType.SEMANTIC
    semantic_query = query.strip()

    # 1. Detect Intent / Classification
    # Supersession / Lineage
    if any(k in lower_query for k in ["superseded", "supersedes", "supersede", "which decision replaced", "replaced by"]):
        query_type = QueryType.SUPERSESSION
    # Comparison / Changes over time
    elif (
        any(k in lower_query for k in ["what changed", "difference between", "how did it change", "changes between"])
        or re.search(r"\bwhen did .*change\b", lower_query)
        or re.search(r"\bhow did .*evolve\b", lower_query)
    ):
        query_type = QueryType.COMPARISON
    # Source provenance inquiry
    elif any(k in lower_query for k in ["where did i write", "which file", "which note", "what source"]):
        query_type = QueryType.SOURCE_LOOKUP
    # Current / Latest State
    elif any(re.search(rf"\b{word}\b", lower_query) for word in ["current", "currently", "latest", "now", "present"]):
        query_type = QueryType.CURRENT_STATE
        temporal_range = TemporalRange(
            temporal_type=TemporalType.VALIDITY_TIME,
            target_status="active",
            description="Currently active knowledge",
        )
    # Historical / Previous State
    elif any(re.search(rf"\b{word}\b", lower_query) for word in ["previous", "previously", "old", "earlier", "former", "historical", "past", "originally"]):
        query_type = QueryType.HISTORICAL
        temporal_range = TemporalRange(
            temporal_type=TemporalType.VALIDITY_TIME,
            target_status="superseded",
            description="Historical or superseded knowledge",
        )

    # 2. Extract Relative and Absolute Temporal Expressions
    # Match "last <month>" (e.g. "last March")
    last_month_match = re.search(
        r"\blast\s+(" + "|".join(MONTH_NAMES) + r")\b",
        lower_query
    )
    if last_month_match:
        query_type = QueryType.TEMPORAL
        month_name = last_month_match.group(1)
        target_month = MONTH_MAP[month_name]
        # If target month is >= reference month, it refers to the previous calendar year
        target_year = ref_dt.year if target_month <= ref_dt.month else ref_dt.year - 1
        start_dt, end_dt = get_month_range(target_year, target_month)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description=f"{month_name.capitalize()} {target_year}",
        )
        # Clean semantic query
        semantic_query = re.sub(r"\blast\s+" + month_name + r"\b", "", semantic_query, flags=re.IGNORECASE).strip()

    # Match "in <Month> <YYYY>" or "in <Month>" (e.g., "in March 2026", "in March")
    month_year_match = re.search(
        r"\b(?:in|during|for)\s+(" + "|".join(MONTH_NAMES) + r")(?:\s+(\d{4}))?\b",
        lower_query
    )
    if not last_month_match and month_year_match:
        query_type = QueryType.TEMPORAL
        month_name = month_year_match.group(1)
        year_str = month_year_match.group(2)
        target_month = MONTH_MAP[month_name]
        target_year = int(year_str) if year_str else ref_dt.year
        start_dt, end_dt = get_month_range(target_year, target_month)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description=f"{month_name.capitalize()} {target_year}",
        )
        pattern_to_remove = month_year_match.group(0)
        semantic_query = semantic_query.replace(pattern_to_remove, "").strip()

    # Match "in <YYYY>" (e.g. "in 2026", "in 2020")
    year_match = re.search(r"\b(?:in|during)\s+(\d{4})\b", lower_query)
    if not temporal_range and year_match:
        query_type = QueryType.TEMPORAL
        target_year = int(year_match.group(1))
        start_dt, end_dt = get_year_range(target_year)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description=f"Year {target_year}",
        )
        semantic_query = semantic_query.replace(year_match.group(0), "").strip()

    # Match "last month"
    if "last month" in lower_query:
        query_type = QueryType.TEMPORAL
        target_month = ref_dt.month - 1 or 12
        target_year = ref_dt.year if ref_dt.month > 1 else ref_dt.year - 1
        start_dt, end_dt = get_month_range(target_year, target_month)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description=f"Last month ({target_month}/{target_year})",
        )
        semantic_query = re.sub(r"\blast month\b", "", semantic_query, flags=re.IGNORECASE).strip()

    # Match "this month"
    if "this month" in lower_query:
        query_type = QueryType.TEMPORAL
        start_dt, end_dt = get_month_range(ref_dt.year, ref_dt.month)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description=f"This month ({ref_dt.month}/{ref_dt.year})",
        )
        semantic_query = re.sub(r"\bthis month\b", "", semantic_query, flags=re.IGNORECASE).strip()

    # Match "yesterday"
    if "yesterday" in lower_query:
        query_type = QueryType.TEMPORAL
        yd = ref_dt - timedelta(days=1)
        start_dt = datetime(yd.year, yd.month, yd.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(yd.year, yd.month, yd.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        temporal_range = TemporalRange(
            start_date=start_dt,
            end_date=end_dt,
            temporal_type=TemporalType.EVENT_TIME,
            description="Yesterday",
        )
        semantic_query = re.sub(r"\byesterday\b", "", semantic_query, flags=re.IGNORECASE).strip()

    # Clean residual auxiliary words like multiple spaces, question mark formatting
    semantic_query = re.sub(r"\s+", " ", semantic_query).strip()
    if semantic_query.endswith(" ?"):
        semantic_query = semantic_query[:-2] + "?"

    return ParsedQuery(
        original_query=query,
        semantic_query=semantic_query,
        query_type=query_type,
        temporal_range=temporal_range,
    )
