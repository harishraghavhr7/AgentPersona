from typing import List, Optional
from pydantic import BaseModel


class EvalSample(BaseModel):
    id: str
    query: str
    expected_query_type: str
    expected_source: Optional[str] = None
    expected_event_date_prefix: Optional[str] = None
    expected_status: Optional[str] = None
    expected_in_answer: Optional[str] = None
    is_negative: bool = False  # True if expected to yield no evidence / no hallucination


BENCHMARK_DATASET: List[EvalSample] = [
    EvalSample(
        id="q1_temporal_march",
        query="What did I decide about the database last March?",
        expected_query_type="TEMPORAL",
        expected_source="database_decision.md",
        expected_event_date_prefix="2026-03-15",
        expected_status="superseded",
        expected_in_answer="postgresql",
    ),
    EvalSample(
        id="q2_current_state",
        query="What is my current production database decision?",
        expected_query_type="CURRENT_STATE",
        expected_source="database_decision.md",
        expected_event_date_prefix="2026-08-10",
        expected_status="active",
        expected_in_answer="postgresql",
    ),
    EvalSample(
        id="q3_historical",
        query="What was my previous database decision?",
        expected_query_type="HISTORICAL",
        expected_source="database_decision.md",
        expected_status="superseded",
        expected_in_answer="sqlite",
    ),
    EvalSample(
        id="q4_comparison",
        query="When did my database decision change?",
        expected_query_type="COMPARISON",
        expected_source="database_decision.md",
        expected_in_answer="may 20",
    ),
    EvalSample(
        id="q5_out_of_range",
        query="What did I decide about databases in January 2020?",
        expected_query_type="TEMPORAL",
        expected_source=None,
        is_negative=True,
    ),
]
