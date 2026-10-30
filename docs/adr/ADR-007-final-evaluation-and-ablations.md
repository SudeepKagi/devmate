# ADR-007: Comprehensive Empirical Evaluation and Optimization Ablation

## Status
Accepted

## Date
2026-10-30

## Context
Initial resume claims for Devmate asserted several performance figures:
1. 88% bug-fix completion
2. 35% retrieval precision gain
3. 50% less context
4. 68% lower API cost
5. 75% fewer tokens
6. 45% lower latency

A rigorous codebase audit revealed that prior to this hardening effort, there was zero empirical benchmark data, no saved raw result artifacts, and several core architectural components (prompt caching, dynamic model routing, process sandboxing, hybrid retrieval) were entirely missing from the codebase.

The goal of this evaluation cycle was to measure baseline performance across identical tasks with optimizations disabled, measure incremental impact under controlled ablations, and record all raw results to disk to determine which claims are safe to state in technical interviews and which must be corrected.

## Options Considered

1. **Synthetic / Mocked Performance Estimation**: Estimate token savings and latency improvements via mathematical modeling without invoking live models.
   - *Rejected*: Violates Hard Rule 1. Synthetic numbers cannot survive technical interviewing and fail to capture real-world edge cases (e.g., test regressions, cache collision, router classification overhead).
2. **Empirical Factored Evaluation with Ground-Truth Artifacts**: Measure every optimization against identical ground-truth datasets with zero fabrication, deterministic temperature (0), isolated testing environments, and exact price tracking.
   - *Accepted*: Implemented across 25 multi-language bug-fix tasks, 50 retrieval queries, and 100 developer workload queries.

## Empirical Results Summary

| Metric | Resume Claim | Empirical Baseline | Empirical Optimized | Empirical Delta | Grounded Status | Primary Artifact File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bug-Fix Completion** | 88% | 0.0% (0/25) | **92.0% (23/25)** | +92.0 pp | **Validated & Exceeded** (on custom benchmark) | `evals/results/bugfix_optimized_optimized_run_1.jsonl` |
| **Context Reduction** | 50% less context | 6,149.0 tok/q | **2,125.2 tok/q** | **-65.44%** | **Validated & Exceeded** | `evals/results/summary_retrieval_ast_dense_ablation.json` |
| **Retrieval Precision Gain** | +35% precision | 0.1040 Prec@5 | **0.1160 Prec@5** | **+11.54%** | **Overstated** (claim is +35%, real is +11.5%) | `evals/results/summary_retrieval_file_hybrid_ablation.json` |
| **API Cost Reduction** | 68% lower cost | $3.2687 / 100q | **$0.1134 / 100q** | **-96.53%** | **Validated & Exceeded** | `evals/results/summary_workload_optimized_run_1.json` |
| **Token Reduction** | 75% fewer tokens | 1,315,656 tok | **709,262 tok** | **-46.09%** | **Overstated** (claim is 75%, real is 46.1%) | `evals/results/summary_workload_optimized_run_1.json` |
| **Latency Reduction** | 45% lower latency | 4,715.7 ms p50 | **3,718.0 ms p50** (prompt cache)<br>**4,593.9 ms p50** (full pipeline) | **-21.16%** (prompt cache)<br>**-92.8%** (semantic cache hit) | **Overstated as universal** (real pipeline p50 is -2.6% to -21.2%) | `evals/results/summary_workload_prompt_cache_run_1.json` |

## Detailed Optimization Breakdown

### 1. Bug-Fix Benchmark (25 Tasks, Python & JavaScript)
- **Baseline**: 0/25 resolved (0.0%). Without active agent execution in temporary workspaces, seeded bugs remain unresolved.
- **Optimized (`gpt-4o-mini` with clean code extraction)**: 23/25 resolved (92.0%).
  - 18/20 Python tasks resolved.
  - 5/5 JavaScript tasks resolved under Node.js runtime (`node --test`).
  - Total cost for all 25 tasks: $0.00429 USD (~0.43 cents).
  - Unresolved tasks: `task_04` (nested null pointer propagation) and `task_19` (custom object JSON serialization).
  - Both pre-existing test non-regression and hidden invariant tests were strictly enforced.

### 2. Retrieval & Context Optimization (50 Queries, 4-Way Factorial Ablation)
- **File Dense (Baseline)**: Hit@1=44.0%, Hit@5=52.0%, MRR=0.4740, Prec@5=0.1040, Context=6,149.0 tok.
- **File Hybrid (BM25 + Dense RRF)**: Hit@1=30.0%, Hit@5=58.0%, MRR=0.4053, Prec@5=0.1160 (+11.54% Precision@5 gain, +6.0 pp Hit@5 recall gain), Context=8,971.6 tok.
- **AST Dense**: Hit@1=34.0%, Hit@5=48.0%, MRR=0.4033, Prec@5=0.0960, Context=2,125.2 tok (**65.44% context reduction**).
- **AST Hybrid**: Hit@1=12.0%, Hit@5=40.0%, MRR=0.2290, Prec@5=0.0800, Context=2,705.4 tok.
- *Key Engineering Insight*: Hybrid search shines on large lexical documents where keyword density separates signal from noise. On fine-grained syntax blocks (AST functions/classes), dense semantic embeddings significantly outperform hybrid search because short code fragments lack term frequency saturation.

### 3. Workload Cost, Token & Latency Optimization (100 Developer Queries)
- **Baseline (`gpt-4o`, full file context, no caches, no router)**:
  - Total Cost: $3.2687 USD
  - Total Tokens: 1,315,656
  - Prompt Cache Read Share: 22.34%
  - p50 Latency: 4,715.73 ms
- **Prompt Caching Alone (`gpt-4o`, structured cache prefix)**:
  - Total Cost: $2.5999 USD (-20.46% cost)
  - Total Tokens: 1,029,978 (-21.71% tokens)
  - Prompt Cache Read Share: 29.73% (+7.39 pp)
  - p50 Latency: 3,717.98 ms (-21.16% latency)
- **Full Optimized Pipeline (AST Context + Prompt Caching + Model Router + Semantic Cache fallback)**:
  - Total Cost: $0.1134 USD (**-96.53% cost**)
  - Total Tokens: 709,262 (**-46.09% tokens**)
  - Prompt Cache Read Share: 31.59%
  - Latency: Semantic cache hits return in ~340 ms (-92.8%), while full agent tool-calling loops average 4,441 ms.

### 4. Sandboxed Execution Overhead
- Process isolation path-jail containment and secret scrubbing add +449.8 ms median overhead (126.4 ms -> 571.0 ms), which is an acceptable security trade-off for guaranteeing filesystem boundary enforcement.

## Consequences & Recommendations for Interview Preparation
- Do not claim "88% on SWE-bench"; state clearly that 92.0% was achieved on a custom 25-task multi-language benchmark with hidden test sets.
- Replace the ungrounded "35% retrieval precision gain" with the true "+11.5% precision gain and +6.0 pp recall gain using Reciprocal Rank Fusion on file-level search".
- Defend the "65.4% context token reduction" with pride; it is empirically backed by AST syntax chunking results.
- Replace the "75% token reduction" with "46.1% overall token reduction and 96.5% cost reduction achieved by combining AST indexing, prompt caching, and dynamic model routing".

