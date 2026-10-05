from typing import List, Dict, Any
from models.query import SourceCitation, QueryResponse
from .dataset import EvalSample


def compute_retrieval_metrics(
    sample: EvalSample,
    citations: List[SourceCitation],
    k: int = 5,
) -> Dict[str, float]:
    """
    Compute Recall@K, Precision@K, and Reciprocal Rank (RR) for a sample.
    """
    top_cits = citations[:k]

    if sample.is_negative:
        # Negative sample: perfect if 0 items retrieved
        recall = 1.0 if len(top_cits) == 0 else 0.0
        precision = 1.0 if len(top_cits) == 0 else 0.0
        rr = 1.0 if len(top_cits) == 0 else 0.0
        return {"recall@k": recall, "precision@k": precision, "mrr": rr}

    hits = 0
    rr = 0.0
    for idx, c in enumerate(top_cits):
        source_match = sample.expected_source in c.source if sample.expected_source else True
        date_match = (
            c.event_at.startswith(sample.expected_event_date_prefix)
            if sample.expected_event_date_prefix and c.event_at
            else True
        )
        status_match = (c.status == sample.expected_status) if sample.expected_status else True

        if source_match and date_match and status_match:
            hits += 1
            if rr == 0.0:
                rr = 1.0 / (idx + 1)

    recall = 1.0 if hits > 0 else 0.0
    precision = (hits / len(top_cits)) if top_cits else 0.0

    return {
        "recall@k": recall,
        "precision@k": precision,
        "mrr": rr,
    }


def compute_generation_metrics(
    sample: EvalSample,
    response: QueryResponse,
) -> Dict[str, float]:
    ans = response.answer.lower()

    if sample.is_negative:
        # Must report insufficient evidence, without hallucinating facts
        faithfulness = 1.0 if ("sufficient evidence" in ans or "no evidence" in ans) else 0.0
        return {"faithfulness": faithfulness, "temporal_accuracy": 1.0}

    # Entity/answer match
    faithfulness = 1.0 if (sample.expected_in_answer and sample.expected_in_answer in ans) else 0.0

    # Temporal query type classification accuracy
    type_acc = 1.0 if response.query_type.value == sample.expected_query_type else 0.0

    return {
        "faithfulness": faithfulness,
        "temporal_accuracy": type_acc,
    }
