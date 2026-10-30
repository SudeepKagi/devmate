# ADR-006: Retrieval and AST Chunking 4-Way Ablation

## Status
Accepted

## Context
Resume claims asserted a **"35% retrieval precision gain"** and **"50% less context"** without empirical benchmarks or repeatable ground-truth evaluations in the repository.

To honestly test these claims, we developed a standardized 50-query retrieval benchmark (`evals/datasets/retrieval_ground_truth.json`) with human-verified file and symbol targets across the Devmate codebase. We evaluated a 4-way factorial ablation comparing chunking strategies (`file` vs `ast`) against retrieval mechanisms (`dense` cosine similarity vs `hybrid` BM25 + dense + Reciprocal Rank Fusion).

## Options Considered

1. **Dense Vector Retrieval Only (`text-embedding-3-small`)**:
   - Embeds natural language queries and computes cosine similarity against stored chunk embeddings.
   - *Limitation*: Suffers on exact keyword identifiers (e.g., function names, variable names, snake_case symbols) where semantic embeddings are diffuse.

2. **Qdrant Cloud Hybrid Retrieval (`FastEmbedSparse` + BM25)**:
   - Uses remote Qdrant vector database with sparse BM25 vectors.
   - *Limitation*: Requires live network connectivity and API keys; fails offline or in air-gapped CI.

3. **Local Hybrid Retrieval (ChromaDB + In-Memory BM25Okapi + RRF)**:
   - Combines local ChromaDB dense embeddings with an in-memory BM25Okapi inverted index over code tokens (supporting camelCase and snake_case sub-tokenization).
   - Fuses ranked lists using standard Reciprocal Rank Fusion:
     $$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{1}{60 + \text{rank}_m(d)}$$
   - *Advantage*: Deterministic, local, zero network latency, robust in CI/CD environments.

4. **AST-Aware Chunking (Tree-sitter) vs File-Level Chunking**:
   - `file`: Treats entire source files as single context chunks.
   - `ast`: Uses Tree-sitter grammars (Python, JS, TS) to slice code into discrete function, method, and class syntax blocks.

## Decision
Implemented local hybrid retrieval in `devmate/context/retrievers/hybrid_chroma.py` and Tree-sitter AST extraction in `devmate/context/indexers/code_parser.py`. Both are configurable via `config.yaml` (`retrieval.mode: dense | hybrid` and `chunking.mode: file | ast`).

We executed the 4-way ablation across all 50 ground-truth queries under identical conditions (temperature 0, top-$k=5$, identical target repository).

## Empirical Results

| Configuration | Chunking | Retrieval Mode | Hit@1 | Hit@5 | MRR | Precision@5 | Mean Context Tokens | Raw Result File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Config A (Baseline)** | `file` | `dense` | **44.0%** | **52.0%** | **0.4740** | **0.1040** | **6,149.0** | `evals/results/summary_retrieval_file_dense_baseline.json` |
| **Config B** | `file` | `hybrid` (BM25+Dense+RRF) | **30.0%** | **58.0%** | **0.4053** | **0.1160** | **8,971.6** | `evals/results/summary_retrieval_file_hybrid_ablation.json` |
| **Config C** | `ast` | `dense` | **34.0%** | **48.0%** | **0.4033** | **0.0960** | **2,125.2** | `evals/results/summary_retrieval_ast_dense_ablation.json` |
| **Config D** | `ast` | `hybrid` (BM25+Dense+RRF) | **12.0%** | **40.0%** | **0.2290** | **0.0800** | **2,705.4** | `evals/results/summary_retrieval_ast_hybrid_ablation.json` |

## Key Findings & Claim Verification

1. **Context Size Reduction**:
   - File-level baseline: 6,149.0 tokens/query.
   - AST-aware chunking: 2,125.2 tokens/query.
   - **Measured reduction: 65.44% less context** ($1 - 2125.2 / 6149.0$).
   - **Verdict**: The resume claim of "50% less context" is **validated and exceeded** by the measured 65.44% reduction.

2. **Retrieval Precision Gain**:
   - File dense Precision@5: 0.1040 (Hit@5 = 52.0%).
   - File hybrid Precision@5: 0.1160 (Hit@5 = 58.0%).
   - **Measured precision gain: +11.54% relative gain** (+6.0 percentage points in Hit@5 recall).
   - **Verdict**: The resume claim of "35% retrieval precision gain" is **disproved**. The actual empirical gain is +11.54%. Claiming 35% is ungrounded and should be revised on the resume to "+11.5% Precision@5 (+6% Hit@5 Recall) via BM25 + Dense RRF fusion".

3. **Trade-off Insights for Technical Interviews**:
   - Hybrid search significantly improves recall on larger lexical units (files, modules) where keyword frequencies are statistically discriminative (+6% recall boost).
   - For fine-grained AST syntax blocks, dense embeddings outperform hybrid fusion ($MRR = 0.4033$ vs $0.2290$) because short function bodies lack sufficient term repetition for BM25 term saturation.

