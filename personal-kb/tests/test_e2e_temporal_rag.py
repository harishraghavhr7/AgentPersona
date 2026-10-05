import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
import pytest
from generation.answer import GenerationService
from models.query import QueryType


@pytest.fixture(scope="module")
def gen_service():
    return GenerationService()


@pytest.fixture(scope="module")
def ref_date():
    return datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_query_last_march(gen_service, ref_date):
    resp = gen_service.generate_answer("What did I decide about the database last March?", reference_date=ref_date)
    assert resp.query_type == QueryType.TEMPORAL
    assert len(resp.sources) >= 1
    assert "postgresql" in resp.answer.lower()


def test_query_current_decision(gen_service, ref_date):
    resp = gen_service.generate_answer("What is my current production database decision?", reference_date=ref_date)
    assert resp.query_type == QueryType.CURRENT_STATE
    assert "postgresql" in resp.answer.lower()
    assert any(s.status == "active" for s in resp.sources)


def test_query_previous_decision(gen_service, ref_date):
    resp = gen_service.generate_answer("What was my previous database decision?", reference_date=ref_date)
    assert resp.query_type == QueryType.HISTORICAL
    assert "sqlite" in resp.answer.lower() or "postgresql" in resp.answer.lower()


def test_query_decision_changes(gen_service, ref_date):
    resp = gen_service.generate_answer("When did my database decision change?", reference_date=ref_date)
    assert resp.query_type == QueryType.COMPARISON
    ans_lower = resp.answer.lower()
    assert (
        "may 20" in ans_lower
        or "august 10" in ans_lower
        or "changed" in ans_lower
        or "2026-05-20" in ans_lower
        or "2026-08-10" in ans_lower
    )


def test_query_out_of_range_no_hallucination(gen_service, ref_date):
    resp = gen_service.generate_answer("What did I decide about databases in January 2020?", reference_date=ref_date)
    assert resp.query_type == QueryType.TEMPORAL
    assert len(resp.sources) == 0
    assert "sufficient evidence" in resp.answer.lower()
