# ADR-002: Benchmark Datasets and Baseline Protocol Specification

## Status
Accepted

## Date
2026-10-30

## Context and Problem Statement
Previous claims regarding Devmate performance (88% bug-fix completion, 35% retrieval precision gain, 50% less context, 68% lower API cost, 75% fewer tokens, 45% lower latency) lacked empirical backing and verifiable datasets. To establish an untampered benchmark:
1. Benchmark tasks and ground-truth datasets must be authored and frozen **before** running experiments (Hard Rule 2).
2. The baseline must be evaluated on the exact same tasks and queries with all optimizations disabled: full-file context (`chunking.mode: file`), dense-only retrieval (`retrieval.mode: dense`), no semantic cache (`semantic_cache.enabled: false`), no prompt caching (`prompt_caching.enabled: false`), and no router (`router.enabled: false`).
3. Results must be saved in structured JSONL files in `evals/results/`.

## Datasets Authored and Frozen

### 1. Retrieval Benchmark (`evals/datasets/retrieval_ground_truth.json`)
- **Size**: 50 queries spanning the entire `devmate` codebase (configuration, agent loop, RAG, retrievers, safety guardrails, HITL, planner, task store, tools, skills, memory).
- **Ground Truth**: Human-labeled exact target file and target symbol (function, class, or constant). Zero LLM judging for ground truth.
- **Metrics**: Hit@1, Hit@5, MRR, Precision@5, and context token count.

### 2. Autonomous Bug-Fix Benchmark (`evals/datasets/bugfix_bench/`)
- **Size**: 25 isolated tasks (20 Python, 5 JavaScript) covering diverse realistic bug classes:
  - Off-by-one errors (pagination slice)
  - Mutable default arguments (role manager)
  - Operator mistakes (boundary tiers)
  - Missing null/None checks (nested dict access)
  - Dict key errors (missing headers)
  - Inverted sort order (priority queues)
  - Unawaited coroutines (async cache)
  - Range boundaries (inclusive filtering)
  - Type coercion (string port to integer)
  - Regex anchoring (UUID validation)
  - State leakage (singleton aggregator)
  - Cache eviction ordering (LRU recency)
  - Floating point precision (tax rounding)
  - Shallow copy mutations (template dicts)
  - String slicing errors (slugification)
  - Circular buffer wrapping
  - List mutation during iteration
  - Inverted boolean permissions
  - Serialization failures (datetime JSON)
  - Zero division (average calculation)
  - JS array sorting without comparator
  - JS unawaited promises
  - JS undefined optional chaining
  - JS `var` closure variable capture
  - JS shallow spread mutation
- **Evaluation Protocol**:
  - Each task runs in a fresh temporary directory (`tempfile.mkdtemp()`).
  - Pre-existing tests must pass initially and must remain passing after fix.
  - Reproducing failing test must fail initially and pass after fix.
  - Invariant hidden tests (injected only during grading) must pass.
  - Step budget: $\le 5$ tool steps; time budget: $\le 120$ seconds.

### 3. Cost & Workload Benchmark (`evals/datasets/workload_100_queries.json`)
- **Size**: 100 sequential queries against Devmate.
- **Controlled Distribution**:
  - 60 Unique queries (60%)
  - 20 Exact duplicates (20%) — identical query strings at later time indices
  - 20 Semantic paraphrases (20%) — semantically identical queries phrased differently
- **Metrics**: Total tokens, prompt cache read share, semantic cache hit rate, cost in USD, and latency (p50, p95, mean).

## Decision
Freeze all datasets and evaluation harnesses in git commit prior to conducting baseline runs. No post-hoc benchmark tuning is permitted.

## Trade-offs and Consequences
- **Pros**: Completely reproducible, immune to p-hacking or prompt overfitting.
- **Cons**: 25 isolated task suites require individual workspace isolation during test execution.

