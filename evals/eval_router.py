"""
Devmate Dynamic Model Router Evaluation Script.
Evaluates model routing decisions across the 100-query developer workload.
Measures routing distribution, reasons, cost delta against always-strong, and escalation behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from devmate.config import config
from devmate.llm.router import ModelRouter
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import metrics_tracker, calculate_cost

logger = get_logger(__name__)

WORKLOAD_PATH = Path("evals/datasets/workload_100_queries.json")
RESULTS_DIR = Path("evals/results")


def evaluate_workload_routing() -> Dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "router_decisions_workload.jsonl"
    summary_file = RESULTS_DIR / "summary_router_workload.json"

    with open(WORKLOAD_PATH, "r", encoding="utf-8") as f:
        workload: List[Dict[str, Any]] = json.load(f)

    # Force router on
    config["router"]["enabled"] = True
    router = ModelRouter()
    metrics_tracker.reset()

    decisions = []
    fast_count = 0
    strong_count = 0
    reasons_breakdown: Dict[str, int] = {}

    for item in workload:
        idx = item["index"]
        query = item["query"]
        task_id = f"workload_route_{idx:03d}"

        model, reason, escalated = router.route(
            task_type="query",
            query=query,
            task_id=task_id,
        )

        if model == router.fast_model:
            fast_count += 1
        else:
            strong_count += 1

        reasons_breakdown[reason] = reasons_breakdown.get(reason, 0) + 1

        rec = {
            "index": idx,
            "query": query,
            "selected_model": model,
            "reason": reason,
            "escalated": escalated,
        }
        decisions.append(rec)
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    total = len(decisions)
    fast_share = (fast_count / total * 100.0) if total else 0.0
    strong_share = (strong_count / total * 100.0) if total else 0.0

    # Calculate theoretical cost savings compared to always-strong on equivalent token payload
    # Average tokens per query in Step 3 was ~10,000 input, ~500 output
    avg_input = 10_000
    avg_output = 500
    avg_cached = 2_900

    always_strong_cost = total * calculate_cost(router.strong_model, avg_input, avg_output, avg_cached)[0]
    routed_cost = (
        fast_count * calculate_cost(router.fast_model, avg_input, avg_output, avg_cached)[0]
        + strong_count * calculate_cost(router.strong_model, avg_input, avg_output, avg_cached)[0]
    )
    cost_savings_pct = ((always_strong_cost - routed_cost) / always_strong_cost * 100.0) if always_strong_cost else 0.0

    summary = {
        "total_queries": total,
        "fast_model": router.fast_model,
        "strong_model": router.strong_model,
        "fast_model_routed_count": fast_count,
        "fast_model_routed_pct": round(fast_share, 2),
        "strong_model_routed_count": strong_count,
        "strong_model_routed_pct": round(strong_share, 2),
        "reasons_breakdown": reasons_breakdown,
        "modeled_always_strong_cost_usd": round(always_strong_cost, 4),
        "modeled_routed_cost_usd": round(routed_cost, 4),
        "modeled_cost_reduction_pct": round(cost_savings_pct, 2),
        "results_file": str(out_file),
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Router Workload Evaluation: Fast={fast_count} ({fast_share:.1f}%), Strong={strong_count} ({strong_share:.1f}%), Modeled Cost Savings={cost_savings_pct:.1f}%")
    return summary


if __name__ == "__main__":
    res = evaluate_workload_routing()
    print(json.dumps(res, indent=2))

