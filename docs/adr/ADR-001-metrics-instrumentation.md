# ADR-001: Empirical LLM Metrics Tracker and Instrumentation Layer

## Status
Accepted

## Date
2026-10-30

## Context and Problem Statement
To honestly evaluate Devmate against the resume claims (token reduction, prompt cache efficiency, API cost savings, latency p50/p95, model routing), every LLM interaction must be tracked with zero fabrication. Previous audit findings revealed that token and cost savings were unverified without persistent execution logs. 

We require an instrumentation layer that:
1. Intercepts all LLM calls across the agent loop, task planner, and evaluation pipelines.
2. Captures provider, model name, input tokens, output tokens, cached tokens (from provider usage metadata), latency in milliseconds, cache hits/misses, and router decisions.
3. Computes estimated cost using an auditable, cited price table in `config.yaml`.
4. Persists structured JSONL logs to disk (`evals/results/`) per task and per benchmark run.

## Options Considered

### Option 1: Rely solely on SaaS Tracing (Confident AI / Langfuse)
- **Pros**: Existing UI for inspection.
- **Cons**: Requires active external SaaS connectivity, API keys, and network calls; offline benchmarks or air-gapped test environments fail; metrics cannot be easily parsed programmatically into local ablation reports.

### Option 2: Monkey-patch low-level HTTP clients (`httpx` / `requests`)
- **Pros**: Catches raw wire traffic.
- **Cons**: High fragility; breaks across provider SDK updates; requires manual deserialization of streaming and chunked server-sent events.

### Option 3: LangChain `BaseCallbackHandler` + `ContextVar` Task Scoping + Local JSONL Writer (Chosen)
- **Pros**:
  - Native integration with LangChain 0.3+ and LangGraph.
  - Extracts normalized `usage_metadata` across OpenAI, Anthropic, and Gemini.
  - Scopes concurrent calls to `task_id` and `run_id` without polluting signature interfaces.
  - Generates verifiable, deterministic, offline-accessible JSONL records for empirical evaluation.
  - Zero external SaaS dependency for metric collection.
- **Cons**: Must maintain a parser for provider-specific response metadata variations (e.g., Anthropic `cache_read_input_tokens` vs. OpenAI `prompt_tokens_details.cached_tokens` vs. Gemini `cached_content_token_count`).

## Decision
We implemented Option 3 in `devmate/observability/metrics_tracker.py`:
1. **Pricing Configuration**: Added an auditable pricing table to `config.yaml` and `devmate/config.py` citing official pricing documentation URLs and effective dates.
2. **`MetricsTracker`**: Singleton and instantiable tracker supporting `task_context` scoping, cost calculations, summary aggregation (call count, tokens, p50/p95 latency, cost), and atomic thread-safe JSONL file writes to `evals/results/`.
3. **`MetricsCallbackHandler`**: Automatically attached in `devmate/llm/factory.py` (`get_llm`), `devmate/tasks/planner.py`, and `devmate/agent/orchestrator.py` (`handle_query`).
4. **Token Extractor**: Robust `extract_token_usage` that unifies `usage_metadata`, `llm_output.token_usage`, and provider `response_metadata`.

## Trade-offs and Consequences
- **Pros**: Every single token, latency measurement, and dollar fraction is grounded in empirical result files on disk. Enables transparent before-and-after ablations.
- **Cons**: Minor disk I/O (~0.1 ms per LLM call) which is negligible compared to network round-trip LLM latency (300–2000 ms).

