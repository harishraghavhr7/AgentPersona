import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
import logging
from typing import Dict, Any, List

from generation.answer import GenerationService
from evaluation.dataset import BENCHMARK_DATASET, EvalSample
from evaluation.metrics import compute_retrieval_metrics, compute_generation_metrics

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """
    Executes automated evaluation across the benchmark dataset and
    computes Recall@K, Precision@K, MRR, Temporal Accuracy, and Faithfulness.
    """

    def __init__(self, service: GenerationService = None):
        self.service = service or GenerationService()
        self.reference_date = datetime(2026, 10, 1, tzinfo=timezone.utc)

    def run_evaluation(self, k: int = 5) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []

        total_recall = 0.0
        total_precision = 0.0
        total_mrr = 0.0
        total_faithfulness = 0.0
        total_temp_acc = 0.0

        print("\n" + "=" * 70)
        print("RUNNING TEMPORAL RAG EVALUATION BENCHMARK")
        print("=" * 70)

        for sample in BENCHMARK_DATASET:
            resp = self.service.generate_answer(
                query=sample.query,
                top_k=k,
                reference_date=self.reference_date,
            )

            ret_m = compute_retrieval_metrics(sample, resp.sources, k=k)
            gen_m = compute_generation_metrics(sample, resp)

            total_recall += ret_m["recall@k"]
            total_precision += ret_m["precision@k"]
            total_mrr += ret_m["mrr"]
            total_faithfulness += gen_m["faithfulness"]
            total_temp_acc += gen_m["temporal_accuracy"]

            sample_summary = {
                "id": sample.id,
                "query": sample.query,
                "type": resp.query_type.value,
                "sources_retrieved": len(resp.sources),
                "recall@k": ret_m["recall@k"],
                "precision@k": round(ret_m["precision@k"], 2),
                "mrr": round(ret_m["mrr"], 2),
                "faithfulness": gen_m["faithfulness"],
                "temp_accuracy": gen_m["temporal_accuracy"],
            }
            results.append(sample_summary)
            print(f"[{sample.id}] Recall@{k}: {ret_m['recall@k']} | MRR: {ret_m['mrr']:.2f} | Faithfulness: {gen_m['faithfulness']}")

        n = len(BENCHMARK_DATASET)
        summary = {
            "num_samples": n,
            f"mean_recall@{k}": round(total_recall / n, 4),
            f"mean_precision@{k}": round(total_precision / n, 4),
            "mean_mrr": round(total_mrr / n, 4),
            "mean_faithfulness": round(total_faithfulness / n, 4),
            "temporal_accuracy": round(total_temp_acc / n, 4),
            "detailed_results": results,
        }

        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY RESULTS:")
        print(f"  Mean Recall@{k}:      {summary[f'mean_recall@{k}'] * 100:.1f}%")
        print(f"  Mean Precision@{k}:   {summary[f'mean_precision@{k}'] * 100:.1f}%")
        print(f"  Mean MRR:            {summary['mean_mrr']:.4f}")
        print(f"  Answer Faithfulness: {summary['mean_faithfulness'] * 100:.1f}%")
        print(f"  Temporal Accuracy:   {summary['temporal_accuracy'] * 100:.1f}%")
        print("=" * 70 + "\n")

        return summary


if __name__ == "__main__":
    runner = EvaluationRunner()
    runner.run_evaluation()
