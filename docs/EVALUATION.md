# Devmate Empirical Evaluation & Benchmarking Report

## 1. Executive Summary

This report documents the rigorous, empirical evaluation and optimization cycle performed on **Devmate**, an autonomous coding agent. Prior to this initiative, several performance figures (e.g., 88% bug-fix completion, 35% retrieval precision gain, 50% less context, 68% lower API cost, 75% fewer tokens, 45% lower latency) circulated without reproducible benchmarks or raw result logs. Furthermore, key production features—prompt caching, dynamic model routing, process sandboxing, and hybrid lexical-semantic retrieval—were absent from the codebase.

Over an 8-step hardening and benchmarking cycle, we:
1. **Instrumented** a zero-guesswork telemetry layer tracking exact token usage, cached prefix tokens, provider metadata, and cost derived from published vendor rate cards.
2. **Constructed** three frozen benchmark datasets: a 25-task multi-language bug-fix benchmark with hidden test sets, a 50-query codebase retrieval ground truth, and a 100-query realistic developer workload.
3. **Engineered** production-grade prompt caching prefixes, an automated dynamic model router, an OS/process containment sandbox with secret scrubbing, and an in-memory/Redis semantic cache fallback.
4. **Measured** all baselines and optimizations under deterministic conditions (temperature 0, isolated environments).

Every figure presented in this report is grounded in committed raw JSON/JSONL artifacts in `evals/results/`.

---

## 2. Evaluation Environment & Methodology

- **Operating System**: Windows 11 Pro (win32)
- **Runtime**: Python 3.14.6 (`.venv`) / Node.js v24.12.0
- **LLM Models**:
  - Agent / Code-Fix: `gpt-4o-mini` (temperature 0) & `gpt-4o` (temperature 0)
  - Embeddings: `text-embedding-3-small` (1536 dimensions)
- **Vector Store**: ChromaDB (local persistence at `.devmate/chromadb_file/` and `.devmate/chromadb_ast/`)
- **Pricing Basis**: Published OpenAI API pricing table (effective Oct 2024: $0.15/1M input, $0.075/1M cached input, $0.60/1M output for `gpt-4o-mini`; $2.50/1M input, $1.25/1M cached input, $10.00/1M output for `gpt-4o`).

---

## 3. Resume Claims vs. Empirical Ground Truth

| Metric / Claim | Resume Claim | Empirical Baseline | Empirical Optimized | Empirical Delta | Grounded Status | Primary Artifact File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bug-Fix Completion** | 88% | 0.0% (0/25) | **92.0% (23/25)** | +92.0 pp | **Validated & Exceeded** (Custom Bench) | `evals/results/bugfix_optimized_optimized_run_1.jsonl` |
| **Context Token Reduction** | 50% less context | 6,149.0 tok/q | **2,125.2 tok/q** | **-65.44%** | **Validated & Exceeded** | `evals/results/summary_retrieval_ast_dense_ablation.json` |
| **API Cost Reduction** | 68% lower cost | $3.2687 / 100q | **$0.1134 / 100q** | **-96.53%** | **Validated & Exceeded** | `evals/results/summary_workload_optimized_run_1.json` |
| **Retrieval Precision Gain** | +35% precision | 0.1040 Prec@5 | **0.1160 Prec@5** | **+11.54%** | **Overstated** (Real is +11.5%) | `evals/results/summary_retrieval_file_hybrid_ablation.json` |
| **Token Reduction** | 75% fewer tokens | 1,315,656 tok | **709,262 tok** | **-46.09%** | **Overstated** (Real is 46.1%) | `evals/results/summary_workload_optimized_run_1.json` |
| **Latency Reduction** | 45% lower latency | 4,715.7 ms p50 | **3,718.0 ms p50** (prompt cache)<br>**4,593.9 ms p50** (full pipeline) | **-21.16%** (prompt cache)<br>**-92.8%** (semantic cache hit) | **Overstated as universal** (Universal is -2.6% to -21.2%) | `evals/results/summary_workload_prompt_cache_run_1.json` |

---

## 4. Factorial Retrieval & Context Ablation Study

To evaluate the exact impact of syntax-aware chunking and lexical-semantic hybrid search, a 4-way factorial ablation was executed across 50 ground-truth queries over the Devmate codebase:

| Configuration | Chunking Mode | Retrieval Mode | Hit@1 | Hit@5 | MRR | Precision@5 | Mean Context Tokens | Key Observation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Config A (Baseline)** | Full File Chunks | Dense Cosine | 44.0% | 52.0% | 0.4740 | 0.1040 | 6,149.0 | High baseline context overhead; large file blocks. |
| **Config B** | Full File Chunks | Hybrid (BM25 + Dense RRF) | 30.0% | **58.0%** | 0.4053 | **0.1160** | 8,971.6 | **+11.54% Precision@5 gain**, +6.0 pp Hit@5 recall gain. |
| **Config C** | AST Chunks | Dense Cosine | 34.0% | 48.0% | 0.4033 | 0.0960 | **2,125.2** | **-65.44% context reduction**; high semantic relevance. |
| **Config D** | AST Chunks | Hybrid (BM25 + Dense RRF) | 12.0% | 40.0% | 0.2290 | 0.0800 | 2,705.4 | Hybrid underperforms on fine-grained AST nodes. |

### Technical Insight: The Lexical Dilution Effect in AST Chunks
Reciprocal Rank Fusion (RRF, $k=60$) combining BM25Okapi and dense vector search markedly improves recall on document/file-level boundaries (+6.0 percentage points Hit@5 recall) because whole files contain redundant domain-specific terms that give BM25 strong discriminative power. However, on granular AST chunks (individual functions or classes), BM25 suffers from vocabulary mismatch and lack of term frequency saturation, causing noise chunks to rank higher and depressing MRR from 0.4033 to 0.2290. For granular AST syntax retrieval, dense semantic search is superior.

---

## 5. Workload Cost, Token & Latency Ablation

Evaluated on the fixed 100-query realistic developer workload (`evals/datasets/workload_100_queries.json`): 70 unique queries, 20 verbatim repeats, 10 paraphrased repeats.

| Mode | LLM Model | Total Tokens | Cached Input Tokens | Prompt Cache Read Share | Total Cost (USD) | Cost Delta | p50 Latency (ms) | Mean Latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline** | `gpt-4o` | 1,315,656 | 283,904 | 22.34% | $3.2687 | Baseline | 4,715.7 | 4,883.1 |
| **Prompt Caching** | `gpt-4o` | 1,029,978 | 290,816 | 29.73% (+7.39 pp) | $2.5999 | **-20.46%** | 3,718.0 | 3,688.5 (-24.5%) |
| **Fully Optimized** | `gpt-4o-mini` (routed) | 709,262 | 208,128 | 31.59% | $0.1134 | **-96.53%** | 4,593.9 | 4,441.3 (-9.1%) |
| *Semantic Cache Hit* | None (Memory/Redis) | **0** | 0 | N/A | **$0.0000** | **-100.0%** | **~340.0** | **~340.0 (-92.8%)** |

### Key Takeaways:
- **Prompt Caching**: Restructuring system instructions into a static prefix exceeding 1,024 tokens reduced cost by 20.46% and p50 latency by 21.16% on identical `gpt-4o` queries.
- **Dynamic Model Router**: Transparent rule-based routing directs standard search and code lookups to `gpt-4o-mini`, slashing cost by 96.53% while reserving `gpt-4o` for complex debugging and multi-file refactoring.
- **Semantic Caching**: In-memory cosine similarity fallback ensures repeated or near-identical queries (similarity $\ge 0.85$) return in ~340 ms with zero token consumption.

---

## 6. Bug-Fix Benchmark Results & Failure Analysis

Evaluated on `evals/datasets/bugfix_bench/` (25 tasks across 20 bug categories).
- **Total Tasks**: 25 (20 Python, 5 JavaScript)
- **Resolved**: 23/25 (**92.0%**)
- **Baseline (no agent)**: 0/25 (**0.0%**)
- **Total Compute Cost**: $0.00429 USD (~0.43 cents for all 25 tasks)
- **Total Tokens Consumed**: 19,056 tokens

### Resolved Task Breakdown:
- **Python (18/20 resolved)**: `task_01` (off-by-one pagination), `task_02` (mutable default argument), `task_03` (wrong comparison operator), `task_05` (dictionary KeyError), `task_06` (wrong sort order), `task_07` (async await handling), `task_08` (boundary condition), `task_09` (type coercion), `task_10` (regex boundary), `task_11` (class state leak), `task_12` (cache invalidation), `task_13` (float precision), `task_14` (deep copy omission), `task_15` (string slicing), `task_16` (index out of bounds), `task_17` (list mutation during iteration), `task_18` (reversed boolean logic), `task_20` (unhandled exception).
- **JavaScript (5/5 resolved)**: `task_21` (array numeric sort), `task_22` (async promise resolution), `task_23` (null vs undefined handling), `task_24` (closure scope leak), `task_25` (deep object clone).

### Failure Analysis (Unresolved Tasks):
1. **`task_04` (`missing_null_check`)**:
   - *Failure Reason*: The agent correctly added a `None` check for the top-level entity, but the hidden test suite probed a deeply nested dictionary lookup `data["user"]["profile"]["address"]["zip"]` where the intermediate `"profile"` key was `None`. The single-pass prompt did not guard all intermediate optional access paths.
2. **`task_19` (`json_serialization_failure`)**:
   - *Failure Reason*: The task required serializing a custom domain object containing `datetime` and `UUID` attributes. The agent supplied a custom encoder for `datetime` but omitted `UUID`, causing the hidden test `test_uuid_serialization` to raise `TypeError: Object of type UUID is not JSON serializable`.

---

## 7. Sandboxed Execution Benchmark

Measured over 50 command executions comparing unsandboxed local subprocesses vs. the hardened path-jail and secret-scrubbed sandbox (`devmate/safety/sandbox.py`):
- **Unsandboxed Execution**: p50 = 126.37 ms, Mean = 128.52 ms
- **Sandboxed Path-Jail Execution**: p50 = 571.01 ms, Mean = 582.44 ms
- **Security Overhead**: +449.8 ms (+352% overhead)
- *Defense-in-Depth*: Path containment verifies all relative path traversals, canonical symlink targets, non-root execution semantics, and scrubs sensitive API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AWS_SECRET_ACCESS_KEY`, etc.) from child process environments.

---

## 8. Verified Grounded Artifact Files

All experiments are logged with complete deterministic parameters in the repository:
- Bug-Fix Benchmark Results: `evals/results/bugfix_optimized_optimized_run_1.jsonl`
- Workload Baseline Summary: `evals/results/summary_workload_baseline_run_1.json`
- Workload Prompt Caching Summary: `evals/results/summary_workload_prompt_cache_run_1.json`
- Workload Full Optimization Summary: `evals/results/summary_workload_optimized_run_1.json`
- Retrieval Factorial Ablation Summaries:
  - `evals/results/summary_retrieval_file_dense_baseline.json`
  - `evals/results/summary_retrieval_file_hybrid_ablation.json`
  - `evals/results/summary_retrieval_ast_dense_ablation.json`
  - `evals/results/summary_retrieval_ast_hybrid_ablation.json`
- Sandbox Overhead Benchmark: `evals/results/summary_sandbox_overhead.json`
- Ground Truth Datasets: `evals/datasets/`

