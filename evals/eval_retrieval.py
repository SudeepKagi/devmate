"""
Devmate Retrieval Benchmark Evaluator.
Evaluates Hit@1, Hit@5, MRR, Precision@5, and context token count
against evals/datasets/retrieval_ground_truth.json across chunking and retrieval modes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from devmate.config import config
from devmate.observability.logger import get_logger
from devmate.context.retrievers.factory import get_retriever

logger = get_logger(__name__)

DATASET_PATH = Path("evals/datasets/retrieval_ground_truth.json")
RESULTS_DIR = Path("evals/results")


def estimate_tokens(text: str) -> int:
    """Fast, reliable token estimate based on whitespace and punctuation tokens."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback heuristic: 1 token ~= 4 characters / 0.75 words
        return max(1, int(len(text) / 3.8))


def is_match(chunk: dict, target_file: str, target_symbol: str) -> bool:
    """Check if a retrieved chunk matches the human-labeled ground truth."""
    source = chunk.get("source", "").replace("\\", "/").lower()
    target_f = target_file.replace("\\", "/").lower()
    name = chunk.get("name", "").lower()
    target_s = target_symbol.lower()
    content = chunk.get("content", "").lower()

    file_matches = target_f in source or source.endswith(target_f)

    # Symbol match: exact symbol name, qualified name, or symbol defined inside chunk
    symbol_matches = (
        target_s == name
        or target_s in name
        or f"def {target_s}" in content
        or f"class {target_s}" in content
        or f"{target_s} =" in content
        or f"{target_s}=" in content
    )

    return file_matches and symbol_matches


def evaluate_retrieval(
    mode: str = "dense",
    chunking: str = "ast",
    k: int = 5,
    run_id: str = "run_1",
    repo_path: str = ".",
) -> Dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"retrieval_{chunking}_{mode}_{run_id}.jsonl"
    summary_file = RESULTS_DIR / f"summary_retrieval_{chunking}_{mode}_{run_id}.json"

    # Set configuration mode
    config["chunking"]["mode"] = chunking
    config["vector_store"]["retrieval_mode"] = mode
    config["retrieval"]["mode"] = mode
    config["rag"]["mode"] = "hybrid" if mode == "hybrid" else "semantic"
    config["chromadb"]["persist_dir"] = f".devmate/chromadb_{chunking}/"

    # Ensure codebase is indexed for the requested chunking mode
    if config.get("vector_store", {}).get("provider") == "chroma":
        from devmate.context.indexers.semantic_chroma import index_codebase, _get_collection
        coll = _get_collection(repo_path)
        if coll.count() == 0:
            logger.info(f"Indexing codebase '{repo_path}' with chunking='{chunking}' into ChromaDB...")
            index_codebase(repo_path)

    retrieve_fn = get_retriever()

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        ground_truth: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Evaluating retrieval: mode={mode}, chunking={chunking}, queries={len(ground_truth)}")

    query_results = []
    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    precision_at_5_list = []
    context_tokens_list = []

    for item in ground_truth:
        q_id = item["id"]
        query = item["query"]
        target_file = item["target_file"]
        target_symbol = item["target_symbol"]

        try:
            chunks = retrieve_fn(query, k=k, repo_path=repo_path)
        except Exception as e:
            logger.error(f"Retrieval error for query '{query}': {e}")
            chunks = []

        # Find rank of first match
        first_match_rank = None
        relevant_count = 0
        total_tokens = 0

        for rank, chunk in enumerate(chunks):
            total_tokens += estimate_tokens(chunk.get("content", ""))
            if is_match(chunk, target_file, target_symbol):
                relevant_count += 1
                if first_match_rank is None:
                    first_match_rank = rank + 1  # 1-based rank

        hit_1 = (first_match_rank == 1)
        hit_5 = (first_match_rank is not None and first_match_rank <= 5)
        rr = (1.0 / first_match_rank) if first_match_rank else 0.0
        prec_5 = relevant_count / float(k)

        if hit_1:
            hits_at_1 += 1
        if hit_5:
            hits_at_5 += 1
        reciprocal_ranks.append(rr)
        precision_at_5_list.append(prec_5)
        context_tokens_list.append(total_tokens)

        q_res = {
            "query_id": q_id,
            "query": query,
            "target_file": target_file,
            "target_symbol": target_symbol,
            "hit_at_1": hit_1,
            "hit_at_5": hit_5,
            "first_match_rank": first_match_rank,
            "reciprocal_rank": round(rr, 4),
            "precision_at_5": round(prec_5, 4),
            "context_tokens": total_tokens,
            "retrieved_count": len(chunks),
        }
        query_results.append(q_res)

        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(q_res) + "\n")

    total_queries = len(ground_truth)
    hit_at_1_rate = (hits_at_1 / total_queries) if total_queries else 0.0
    hit_at_5_rate = (hits_at_5 / total_queries) if total_queries else 0.0
    mrr = (sum(reciprocal_ranks) / total_queries) if total_queries else 0.0
    mean_prec_5 = (sum(precision_at_5_list) / total_queries) if total_queries else 0.0
    mean_context_tokens = (sum(context_tokens_list) / total_queries) if total_queries else 0.0

    summary = {
        "mode": mode,
        "chunking": chunking,
        "run_id": run_id,
        "total_queries": total_queries,
        "hit_at_1": round(hit_at_1_rate, 4),
        "hit_at_5": round(hit_at_5_rate, 4),
        "mrr": round(mrr, 4),
        "precision_at_5": round(mean_prec_5, 4),
        "mean_context_tokens": round(mean_context_tokens, 1),
        "results_file": str(out_file),
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Retrieval Summary [{chunking}+{mode}]: Hit@1={hit_at_1_rate:.3f}, Hit@5={hit_at_5_rate:.3f}, MRR={mrr:.3f}, Prec@5={mean_prec_5:.3f}, MeanTokens={mean_context_tokens:.0f}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Devmate Retrieval")
    parser.add_argument("--mode", default="dense", choices=["dense", "hybrid"], help="Retrieval mode")
    parser.add_argument("--chunking", default="ast", choices=["file", "ast"], help="Chunking mode")
    parser.add_argument("--run-id", default="run_1", help="Benchmark run identifier")
    parser.add_argument("--k", type=int, default=5, help="Top-K chunks to retrieve")
    args = parser.parse_args()

    res = evaluate_retrieval(mode=args.mode, chunking=args.chunking, k=args.k, run_id=args.run_id)
    print(json.dumps(res, indent=2))
