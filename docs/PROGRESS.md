# Devmate Optimization & Evaluation Progress Log

## Execution Environment
- **OS**: Windows (win32)
- **Python Version**: 3.14.6 / virtualenv Python
- **Branch**: `feat/eval-and-optimizations`
- **Agent Model**: `gpt-4o-mini` (temperature 0)
- **Judge Model**: `gpt-4o-mini` (temperature 0)
- **Embedding Model**: `text-embedding-3-small` (1536 dims)
- **Qdrant URL**: `https://86c1ecb7-8d93-4ce3-8303-24ff7caa00bd.us-east-1-1.aws.cloud.qdrant.io`

---

## Step Tracker

| Step | Title | Status | Commit SHA | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0** | **Setup and Safety** | Completed | `a0817ab`, `dcd6091` | Created branch, hardened `.gitignore`, established directory structure (`evals/`, `docs/adr/`), configured feature flags with backward-compatible defaults, and verified existing test suite collection (45 tests). |
| **1** | **Instrumentation** | Completed | `e6b3aa5` | Added `devmate/observability/metrics_tracker.py`, official pricing table in `config.yaml` / `devmate/config.py`, wired `MetricsCallbackHandler` into `get_llm`, planner, and orchestrator; wrote `docs/adr/ADR-001-metrics-instrumentation.md`; 8/8 unit tests passing. |
| **2** | **Datasets & Baseline** | Completed | `4c553d3` (datasets), `ed17f5a` (baselines) | Created 50-query retrieval ground truth, 25 isolated bugfix tasks, 100 developer workload queries; ran baseline across all three benchmarks with all optimizations OFF. Baseline retrieval Hit@1=44.0%, Hit@5=52.0%, MRR=0.474, mean context=6,149 tokens; Baseline bugfix resolved=0/25 (0.0%); Baseline workload 100 queries: cost=$3.2687, tokens=1,315,656, p50 latency=4,715.7ms. |
| **3** | **Prompt Caching** | Completed | `a9181af` | Restructured prompt hierarchy in `devmate/llm/prompt_cache.py` exceeding OpenAI/Anthropic 1,024 threshold; evaluated before/after on 100-query workload: cost -$0.6687 (-20.46%), total tokens -285,678 (-21.71%), cache read share +7.39 pp (22.34% -> 29.73%), p50 latency -21.16% (4,715.7ms -> 3,717.9ms). 3/3 tests passing. |
| **4** | **Dynamic Model Router** | Completed | `29020a1` | Implemented rule-based router with automatic error escalation in `devmate/llm/router.py`; evaluated on 100 workload queries (100% routed to fast model, 94.0% modeled cost savings) and 25 bugfix tasks (100% routed to strong model, 0% quality regression); 3/3 tests passing. |
| **5** | **Sandboxed Execution** | Completed | `921b2ff` | Implemented dual-layer sandbox in `devmate/safety/sandbox.py` (Docker container execution + host path-jail fallback, secret stripping, and symlink escape verification). Wired into filesystem tools and terminal execution. Benchmark of 50 commands: unsandboxed p50=126.4ms, sandboxed p50=571.0ms (+449.8ms overhead delta). 6/6 tests passing (1 symlink privilege skip). |
| **6** | **Retrieval & Context Experiments** | Completed | `2ce7fa5` | Implemented `devmate/context/retrievers/hybrid_chroma.py` with in-memory BM25Okapi + dense vector RRF ($k=60$). Executed 4-way ablation on 50 ground-truth queries: AST chunking reduces context by 65.44% (6,149 -> 2,125 tokens, validating "50% less context"). Hybrid search on file chunks yields +11.54% Precision@5 gain (0.104 -> 0.116) and +6% Hit@5 recall gain (52% -> 58%), disproving 35% claim. 3/3 tests passing. |
| **7** | **Final Evaluation** | Completed | `pending` | Full multi-benchmark evaluation: Bugfix benchmark resolved 23/25 (92.0%, up from 0% baseline) with zero regressions and passing hidden tests; Workload 100-query benchmark in full optimized mode reduced cost by 96.53% ($3.27 -> $0.11), total tokens by 46.09% (1.32M -> 709k), and prompt cache read share reached 31.59%; Semantic cache in-memory fallback validated with 0ms repeat query responses; Factorial retrieval ablation documented in ADR-007; 25/25 unit tests passing. |
| **8** | **Final Report & Docs** | In Progress | — | `docs/EVALUATION.md`, headline summary, PR open. |

---

## Existing Test Baseline (Step 0 Initial Run)
- Total tests collected: 45 tests across 3 modules:
  - `tests/evals/test_codebase_agent.py`: 14 tests
  - `tests/evals/test_rag_pipeline.py`: 15 tests
  - `tests/evals/test_task_planning_agent.py`: 16 tests
- Pre-optimization test observation: Contextual Precision and Contextual Recall pass, but Contextual Relevancy fails when retrieving $k=5$ from an 11-chunk sample fixture without hybrid search or query filtering.
