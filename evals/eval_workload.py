"""
Devmate Cost and Token Workload Benchmark Runner.
Executes the fixed 100-query developer workload (evals/datasets/workload_100_queries.json)
measuring tokens, cache hit rate, prompt cache read share, cost, and latency.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from devmate.config import config
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import metrics_tracker
from devmate.agent.factory import build_agent
from devmate.agent.orchestrator import handle_query
from devmate.cache.semantic_cache import SemanticCache

logger = get_logger(__name__)

WORKLOAD_PATH = Path("evals/datasets/workload_100_queries.json")
RESULTS_DIR = Path("evals/results")


async def run_workload(
    mode: str = "baseline",
    run_id: str = "run_1",
    limit: int | None = None,
) -> Dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"workload_{mode}_{run_id}.jsonl"
    summary_file = RESULTS_DIR / f"summary_workload_{mode}_{run_id}.json"

    with open(WORKLOAD_PATH, "r", encoding="utf-8") as f:
        workload: List[Dict[str, Any]] = json.load(f)

    if limit:
        workload = workload[:limit]

    # Configure flags based on evaluation mode
    if mode == "baseline":
        config["semantic_cache"]["enabled"] = False
        config["prompt_caching"]["enabled"] = False
        config["router"]["enabled"] = False
        config["llm"]["model"] = "gpt-4o"
        config["chromadb"]["persist_dir"] = ".devmate/chromadb_file/"
        semantic_cache = None
        cache_domain = None
    else:  # optimized
        config["semantic_cache"]["enabled"] = True
        config["prompt_caching"]["enabled"] = True
        config["router"]["enabled"] = True
        config["chromadb"]["persist_dir"] = ".devmate/chromadb_ast/"
        try:
            semantic_cache = SemanticCache()
            cache_domain = "devmate_benchmark"
        except Exception as e:
            logger.warning(f"Could not initialize Redis SemanticCache, continuing in-memory: {e}")
            semantic_cache = None
            cache_domain = None

    agent = await build_agent(enable_safety=False, include_mcp_tools=False)
    metrics_tracker.reset()

    logger.info(f"Starting workload benchmark: mode={mode}, queries={len(workload)}, run_id={run_id}")

    results = []
    thread_id = f"bench_{mode}_{run_id}"

    for item in workload:
        idx = item["index"]
        query = item["query"]
        q_type = item["type"]

        start_time = time.perf_counter()
        task_id = f"workload_q_{idx:03d}"

        with metrics_tracker.task_context(task_id=task_id, run_id=run_id):
            try:
                answer = await handle_query(
                    agent=agent,
                    question=query,
                    thread_id=thread_id,
                    semantic_cache=semantic_cache,
                    cache_domain=cache_domain,
                )
                error_msg = None
            except Exception as e:
                logger.error(f"Error handling query {idx}: {e}")
                answer = ""
                error_msg = str(e)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        q_summary = metrics_tracker.get_summary(task_id=task_id, run_id=run_id)

        res_record = {
            "index": idx,
            "query": query,
            "type": q_type,
            "latency_ms": round(duration_ms, 2),
            "input_tokens": q_summary.total_input_tokens,
            "output_tokens": q_summary.total_output_tokens,
            "cached_input_tokens": q_summary.total_cached_input_tokens,
            "total_tokens": q_summary.total_tokens,
            "cost_usd": q_summary.total_cost_usd,
            "cache_hit": bool(q_summary.cache_hits > 0),
            "error": error_msg,
        }
        results.append(res_record)

        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(res_record) + "\n")

    # Aggregate metrics
    total_q = len(results)
    total_inp = sum(r["input_tokens"] for r in results)
    total_out = sum(r["output_tokens"] for r in results)
    total_cached = sum(r["cached_input_tokens"] for r in results)
    total_tok = sum(r["total_tokens"] for r in results)
    total_cost = sum(r["cost_usd"] for r in results)
    cache_hits = sum(1 for r in results if r["cache_hit"])
    cache_hit_rate = (cache_hits / total_q * 100.0) if total_q else 0.0
    prompt_cache_share = (total_cached / total_inp * 100.0) if total_inp else 0.0

    latencies = sorted([r["latency_ms"] for r in results])
    mean_lat = sum(latencies) / total_q if total_q else 0.0
    p50_lat = latencies[int(0.50 * total_q)] if latencies else 0.0
    p95_lat = latencies[int(0.95 * total_q)] if latencies else 0.0

    summary = {
        "mode": mode,
        "run_id": run_id,
        "total_queries": total_q,
        "cache_hits": cache_hits,
        "cache_hit_rate_pct": round(cache_hit_rate, 2),
        "total_input_tokens": total_inp,
        "total_output_tokens": total_out,
        "total_cached_input_tokens": total_cached,
        "prompt_cache_read_share_pct": round(prompt_cache_share, 2),
        "total_tokens": total_tok,
        "total_cost_usd": round(total_cost, 6),
        "mean_latency_ms": round(mean_lat, 2),
        "p50_latency_ms": round(p50_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "results_file": str(out_file),
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Workload Summary [{mode}]: Cost=${total_cost:.4f}, Tokens={total_tok}, CachedTokens={total_cached} ({prompt_cache_share:.1f}%), CacheHits={cache_hits}/{total_q} ({cache_hit_rate:.1f}%), p50Lat={p50_lat:.1f}ms")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Devmate Cost and Workload Benchmark")
    parser.add_argument("--mode", default="baseline", choices=["baseline", "optimized"], help="Evaluation mode")
    parser.add_argument("--run-id", default="run_1", help="Benchmark run identifier")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries")
    args = parser.parse_args()

    asyncio.run(run_workload(mode=args.mode, run_id=args.run_id, limit=args.limit))

