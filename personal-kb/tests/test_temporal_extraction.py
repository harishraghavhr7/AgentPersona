import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
import pytest
from temporal.parser import (
    extract_event_date_from_text,
    parse_temporal_query,
    get_month_range,
)
from models.query import QueryType


def test_date_extraction_formats():
    text1 = "On March 15, 2026, I decided to use PostgreSQL."
    d1 = extract_event_date_from_text(text1)
    assert d1 == datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)

    text2 = "Recorded on 2026-05-20 regarding SQLite."
    d2 = extract_event_date_from_text(text2)
    assert d2 == datetime(2026, 5, 20, 0, 0, tzinfo=timezone.utc)

    text3 = "This note has no date whatsoever."
    d3 = extract_event_date_from_text(text3)
    assert d3 is None


def test_query_parsing_relative_month():
    ref = datetime(2026, 10, 1, tzinfo=timezone.utc)
    pq = parse_temporal_query("What did I decide about the database last March?", reference_date=ref)
    assert pq.query_type == QueryType.TEMPORAL
    assert pq.temporal_range is not None
    assert pq.temporal_range.start_date.year == 2026
    assert pq.temporal_range.start_date.month == 3
    assert "last march" not in pq.semantic_query.lower()


def test_query_parsing_current_state():
    ref = datetime(2026, 10, 1, tzinfo=timezone.utc)
    pq = parse_temporal_query("What is my current production database decision?", reference_date=ref)
    assert pq.query_type == QueryType.CURRENT_STATE
    assert pq.temporal_range is not None
    assert pq.temporal_range.target_status == "active"


def test_query_parsing_historical():
    ref = datetime(2026, 10, 1, tzinfo=timezone.utc)
    pq = parse_temporal_query("What was my previous database decision?", reference_date=ref)
    assert pq.query_type == QueryType.HISTORICAL
    assert pq.temporal_range is not None
    assert pq.temporal_range.target_status == "superseded"


def test_query_parsing_comparison():
    ref = datetime(2026, 10, 1, tzinfo=timezone.utc)
    pq = parse_temporal_query("When did my database decision change?", reference_date=ref)
    assert pq.query_type == QueryType.COMPARISON
