# ADR-003: Hierarchical Prompt Restructuring and Prefix Caching Optimization

## Status
Accepted

## Date
2026-10-30

## Context and Problem Statement
In unoptimized LLM agent pipelines, each call sends redundant system prompts, tool schemas, and coding guidelines repeatedly. Major providers (OpenAI, Anthropic, Gemini) support prompt caching to discount repeated prefixes and dramatically lower Time-To-First-Token (TTFT), but enforce strict prerequisites:
1. **OpenAI**: Automatically caches prompts with an identical prefix $\ge 1,024$ tokens (discounting cached tokens by 50%).
2. **Anthropic**: Requires explicit `cache_control: {"type": "ephemeral"}` blocks on sections $\ge 1,024$ tokens (up to 90% discount on cache reads).
3. **Gemini**: Supports explicit Context Caching for large contexts ($\ge 32,768$ tokens).

Prior to this step, Devmate's static prompt was under 500 tokens. As a result, single-turn developer requests never met OpenAI's 1,024 token threshold, resulting in $0 cached tokens on fresh sessions, higher latency (4,883.13 ms mean), and maximum billing ($3.2687 / 100 queries).

## Options Considered

### Option 1: Ad-hoc String Padding
- **Pros**: Easy to push token counts past 1,024.
- **Cons**: Wasteful, uninformative, does not provide architectural value or model grounding.

### Option 2: Full Manual Message Structuring in Every Tool / Orchestrator
- **Pros**: Fine-grained control.
- **Cons**: High code duplication; brittle when new agents or workflows are introduced.

### Option 3: Centralized Hierarchical Prompt Architecture (`devmate/llm/prompt_cache.py`) (Chosen)
- **Pros**:
  - Implements a production-grade static prompt containing core operating principles, detailed tool calling protocols, PEP 8/ES2022 standards, and architectural manuals totaling ~1,100–1,200 tokens.
  - Automatically satisfies OpenAI's $\ge 1,024$ token minimum.
  - Supports Anthropic `cache_control: {"type": "ephemeral"}` metadata.
  - Guarantees strict ordering: static prefix first, tool schemas second, dynamic history and user query strictly last.
- **Cons**: Slightly larger initial payload on the very first cold call.

## Empirical Benchmark Evaluation (Step 2c Workload: 100 Queries)
Evaluated on the exact same 100 developer queries (`evals/datasets/workload_100_queries.json`) with `gpt-4o` at temperature 0:

| Metric | Baseline (`prompt_caching: false`) | Optimized (`prompt_caching: true`) | Empirical Delta | Result File Citations |
| :--- | :--- | :--- | :--- | :--- |
| **Total Cost (USD)** | **$3.268655** | **$2.599925** | **-20.46%** ($0.6687 saved) | [summary_workload_baseline_run_1.json](file:///c:/Projects/claude%20code/evals/results/summary_workload_baseline_run_1.json)<br>[summary_workload_prompt_cache_run_1.json](file:///c:/Projects/claude%20code/evals/results/summary_workload_prompt_cache_run_1.json) |
| **Total Tokens** | **1,315,656** | **1,029,978** | **-21.71%** (285,678 tokens saved) | Same as above |
| **Prompt Cache Read Share** | **22.34%** (283,904 tokens) | **29.73%** (290,816 tokens) | **+7.39 pp** | Same as above |
| **Median Latency (p50)** | **4,715.73 ms** | **3,717.98 ms** | **-21.16%** (997.75 ms faster) | Same as above |
| **Mean Latency** | **4,883.13 ms** | **3,688.52 ms** | **-24.46%** (1,194.61 ms faster) | Same as above |
| **Tail Latency (p95)** | **8,910.93 ms** | **7,620.14 ms** | **-14.49%** (1,290.79 ms faster) | Same as above |

## Decision
Adopt Option 3. Keep `prompt_caching.enabled` configurable via `config.yaml`.

