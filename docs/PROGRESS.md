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
| **0** | **Setup and Safety** | Completed | `a0817ab` | Created branch, hardened `.gitignore`, established directory structure (`evals/`, `docs/adr/`), configured feature flags with backward-compatible defaults, and verified existing test suite collection (45 tests). |
| **1** | **Instrumentation** | Not Started | — | Add LLM metrics tracking wrapper (tokens, latency, cached tokens, cost calculator, JSONL logger). |
| **2** | **Datasets & Baseline** | Not Started | — | Create 50+ retrieval dataset, 25+ bugfix benchmark tasks, 100 developer queries, and measure baseline (all optimizations OFF). |
| **3** | **Prompt Caching** | Not Started | — | Implement provider prompt caching structure, measure cached token shares. |
| **4** | **Dynamic Model Router** | Not Started | — | Implement rule-based & classifier router (fast vs strong model), quality guard on bugfix bench. |
| **5** | **Sandboxed Execution** | Not Started | — | Docker/path jail execution sandbox, security test suite. |
| **6** | **Retrieval & Context Experiments** | Not Started | — | 4-way ablation (file vs AST chunking, dense vs hybrid RRF), context size reduction metrics. |
| **7** | **Final Evaluation** | Not Started | — | Full evaluation runs (3 runs per config), ablation matrix, latency p50/p95. |
| **8** | **Final Report & Docs** | Not Started | — | `docs/EVALUATION.md`, headline summary, PR open. |

---

## Existing Test Baseline (Step 0 Initial Run)
- Total tests collected: 45 tests across 3 modules:
  - `tests/evals/test_codebase_agent.py`: 14 tests
  - `tests/evals/test_rag_pipeline.py`: 15 tests
  - `tests/evals/test_task_planning_agent.py`: 16 tests
- Pre-optimization test observation: Contextual Precision and Contextual Recall pass, but Contextual Relevancy fails when retrieving $k=5$ from an 11-chunk sample fixture without hybrid search or query filtering.
