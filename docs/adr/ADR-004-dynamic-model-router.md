# ADR-004: Dynamic Model Router and Failure Escalation Architecture

## Status
Accepted

## Date
2026-10-30

## Context and Problem Statement
Invoking frontier models (`gpt-4o` at $2.50 / $10.00 per 1M tokens) for every interaction—including trivial lookups, search reformulations, and directory queries—creates excessive API expense without cognitive necessity. Conversely, locking the agent to a compact model (`gpt-4o-mini` at $0.15 / $0.60 per 1M tokens) degrades autonomous bug-fixing, multi-file edits, and architectural DAG planning.

We need a router that:
1. Classifies calls based on task type and complexity without adding extra classification latency.
2. Directs lightweight informational and search tasks to the fast model (`gpt-4o-mini`).
3. Directs high-reasoning tasks (debugging, architecture, bug-fix, planning) to the strong model (`gpt-4o`).
4. Automatically escalates from fast to strong model if a tool error, exception, or validation failure occurs.
5. Guards quality so bug-fix performance does not regress against always-strong.

## Options Considered

### Option 1: Always-Strong Baseline (`gpt-4o`)
- **Pros**: Highest reasoning baseline.
- **Cons**: Up to 16.6x more expensive per input token than `gpt-4o-mini`.

### Option 2: Machine Learning / LLM Classifier Router
- **Pros**: Handles ambiguous prompts.
- **Cons**: Incurs additional latency (300–800 ms) and token overhead for every single prompt before the agent can even begin.

### Option 3: Deterministic Transparent Rules with Automatic Failure Escalation (`devmate/llm/router.py`) (Chosen)
- **Pros**:
  - Zero latency overhead (sub-millisecond regex & rule evaluation).
  - Deterministic and auditable: records exact reasons and flags in `metrics_tracker`.
  - Automatic safety net: immediately escalates session to `strong_model` upon any tool failure or syntax error.
  - Zero degradation on complex tasks: bug-fixing and planning always select `gpt-4o`.
- **Cons**: Relies on curated keywords and task definitions.

## Empirical Benchmark Findings

### 1. Workload Routing Distribution (100 Queries)
Evaluated on `evals/datasets/workload_100_queries.json`:
- **Fast Model (`gpt-4o-mini`)**: 100/100 (100.0%) of read-only exploration and configuration queries.
- **Strong Model (`gpt-4o`)**: 0/100 (0.0%) because all 100 queries were informational questions without bug-fixing requests.
- **Modeled Cost Impact**: $0.1583 USD vs $2.6375 USD on always-strong (**94.0% cost reduction** on read-only queries).
- Citation: [summary_router_workload.json](file:///c:/Projects/claude%20code/evals/results/summary_router_workload.json).

### 2. Quality Guard on Bug-Fix Benchmark (25 Tasks)
Evaluated on `evals/datasets/bugfix_bench/`:
- **Routing Decision**: 25/25 (100.0%) routed directly to `strong_model` (`gpt-4o`) via `high_complexity_task_type (bugfix)` rule.
- **Quality Regression**: 0.0% drop against always-strong baseline.
- Citation: [bugfix_baseline_baseline.jsonl](file:///c:/Projects/claude%20code/evals/results/bugfix_baseline_baseline.jsonl).

## Decision
Adopt Option 3. Keep `router.enabled` configurable via `config.yaml`.

