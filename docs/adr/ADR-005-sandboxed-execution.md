# ADR-005: Sandboxed Execution Architecture and Path-Jail Security

## Status
Accepted

## Date
2026-10-30

## Context and Problem Statement
Autonomous coding agents execute file operations and shell commands. Without strict containment:
1. File tools can traverse above the repository root (e.g., `../../etc/shadow` or `C:\Windows\System32`), exposing host secrets.
2. Malicious symlinks inside a repository can point to sensitive files outside the workspace.
3. Subprocesses inherit developer environment variables, potentially leaking sensitive credentials (`OPENAI_API_KEY`, `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`) to external tools or untrusted scripts.
4. Shell commands can execute fork bombs or consume unbounded CPU/memory.

We require a multi-tier sandbox architecture that prevents path traversal, blocks symlink escapes, scrubs environment secrets, enforces execution timeouts, and runs inside Docker containers when available.

## Options Considered

### Option 1: Basic Regex Command Blocklist (Existing)
- **Pros**: Zero execution latency overhead.
- **Cons**: Completely bypassable via encoding, path traversal, subshells, or indirect script execution.

### Option 2: Docker Container Exclusively
- **Pros**: Full OS-level kernel isolation (cgroups, namespaces).
- **Cons**: Completely blocks execution in developer environments where the Docker daemon is temporarily stopped or unavailable (e.g., Windows Desktop Linux engine down).

### Option 3: Dual-Layer Defense-in-Depth Sandbox (`devmate/safety/sandbox.py`) (Chosen)
- **Pros**:
  - **Path Jail**: Canonical `validate_workspace_path` checks every filesystem tool invocation (`read_file`, `write_file`, `update_file`, `delete_file`, `list_directory`), blocking `../` traversal, absolute path escapes, and symlinks resolving outside the workspace.
  - **Container Isolation (Docker)**: Automatically engages when Docker daemon is active (`--user 1000:1000`, `--network none`, `--memory 512m`, `--cpus 1.0`, `--pids-limit 100`, workspace mount only).
  - **Local Process Jail Fallback**: When Docker is unavailable, enforces path-jailed `cwd`, strict execution timeout, and comprehensive environment secret scrubbing (stripping all `*_KEY`, `*_SECRET`, `*_TOKEN`).
- **Cons**: Incurs subprocess creation and environment sanitization overhead.

## Empirical Overhead Measurement (50 Shell Commands)
Evaluated across a fixed suite of 50 commands comparing un-sandboxed vs. sandboxed execution:

| Metric | Unsandboxed Execution | Sandboxed Execution | Overhead Delta | Result File Citation |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Latency** | **139.22 ms** | **589.05 ms** | **+449.82 ms (+323.09%)** | [summary_sandbox_overhead.json](file:///c:/Projects/claude%20code/evals/results/summary_sandbox_overhead.json) |
| **Median (p50)** | **126.37 ms** | **571.01 ms** | **+444.64 ms** | Same as above |
| **Tail (p95)** | **267.33 ms** | **740.32 ms** | **+472.99 ms** | Same as above |

## Security Verification Suite
Verified in `tests/test_sandbox.py`:
- Path traversal escapes blocked (`SecurityError` on `../../`): **PASS**
- Absolute paths outside workspace jail blocked: **PASS**
- Valid paths inside jail allowed: **PASS**
- Filesystem tools respect jail (`read_file`, `write_file`, `update_file`, `delete_file`): **PASS**
- Environment secret scrubbing (`OPENAI_API_KEY`, etc. stripped): **PASS**
- Execution timeout enforcement: **PASS**

## Decision
Adopt Option 3. Keep `sandbox.enabled` configurable via `config.yaml`.
