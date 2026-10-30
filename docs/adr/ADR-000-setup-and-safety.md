# ADR-000: Setup, Safety Baselines, and Configuration Flags

## Context & Problem
The Devmate autonomous coding agent repository requires systematic hardening, extension of missing capabilities (dynamic model routing, prompt caching, sandboxed execution), and empirical evaluation against grounded baselines. To ensure scientific rigor, all evaluations must be repeatable, transparent, and strictly separated from production defaults.

Key challenges addressed in this initial step:
1. Preventing leakage of API credentials and local vector store state into source control.
2. Establishing configuration flags with safe defaults so all existing functionality remains unbroken while enabling toggling for baseline and optimized ablation runs.
3. Establishing tracking infrastructure (`docs/PROGRESS.md`, `docs/adr/`, `evals/`) to record progress and architectural decisions.

## Options Considered

### Option 1: Inline Configuration Modifications
- Hardcode ablation toggles directly in service constructors or runtime environment variables.
- *Trade-offs*: Fragile, error-prone, hard to reproduce across multiple test runs, high risk of regression.

### Option 2: Centralized Hierarchical Configuration with Dedicated Feature Flags (Chosen)
- Define explicit config flags in `devmate/config.py` and `config.yaml` (`prompt_caching.enabled`, `router.enabled`, `semantic_cache.enabled`, `retrieval.mode`, `chunking.mode`, `sandbox.enabled`).
- Default all flags to preserve current behavior:
  - `prompt_caching.enabled: false`
  - `router.enabled: false`
  - `semantic_cache.enabled: true`
  - `retrieval.mode: "dense"`
  - `chunking.mode: "ast"`
  - `sandbox.enabled: false`
- *Trade-offs*: Requires upfront schema definition, but guarantees deterministic ablation runs where baseline and optimized configurations run identical code under explicit flag states.

## Decision
1. Created dedicated feature branch `feat/eval-and-optimizations`.
2. Hardened `.gitignore` to reject all secrets (`.env*`, `*.key`, `*.pem`, `credentials.json`) and runtime databases (`.devmate/`, `*.db`, `*.sqlite*`, `eval_test_*`).
3. Added structured configuration sections in `devmate/config.py` and `config.yaml`.
4. Initialized tracking directories: `evals/`, `evals/datasets/`, `evals/results/`, `docs/adr/`, and `docs/PROGRESS.md`.

## Consequences & Interview Talking Points
- **Reproducibility**: Any experiment can be reproduced by passing a specific `config.yaml` or setting corresponding environment overrides.
- **Safety First**: By establishing `.gitignore` boundaries prior to adding new evaluation runners and benchmarks, we prevent accidental exposure of enterprise credentials or polluting Git history.
- **Traceability**: Every subsequent optimization step maps to a formal Architecture Decision Record (ADR), creating a defensible engineering log for technical interviews.

