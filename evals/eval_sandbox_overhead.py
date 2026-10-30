"""
Benchmark runner to measure execution latency overhead of sandboxing.
Runs a fixed set of 50 shell commands with and without the sandbox.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from devmate.config import config
from devmate.observability.logger import get_logger
from devmate.tools.terminal_tools import run_command

logger = get_logger(__name__)

RESULTS_DIR = Path("evals/results")

BENCHMARK_COMMANDS = [
    'python -c "print(42)"',
    'python -c "import sys; print(sys.version_info[0])"',
    'python -c "import os; print(os.name)"',
    'python -c "import math; print(math.sqrt(144))"',
    'python -c "import json; print(json.dumps({\'status\': \'ok\'}))"',
    'python -c "print(sum(range(100)))"',
    'python -c "import uuid; print(len(str(uuid.uuid4())))"',
    'python -c "print(\'devmate_test\'.upper())"',
    'python -c "import hashlib; print(hashlib.md5(b\'test\').hexdigest())"',
    'python -c "print(list(reversed([1, 2, 3])))"',
] * 5  # Exactly 50 commands


def run_overhead_benchmark() -> Dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "sandbox_overhead.jsonl"
    summary_file = RESULTS_DIR / "summary_sandbox_overhead.json"

    # 1. Unsandboxed baseline
    config["sandbox"]["enabled"] = False
    unsandboxed_latencies = []
    logger.info("Running 50 commands without sandbox...")
    for idx, cmd in enumerate(BENCHMARK_COMMANDS):
        t0 = time.perf_counter()
        res = run_command.invoke({"command": cmd})
        lat_ms = (time.perf_counter() - t0) * 1000.0
        unsandboxed_latencies.append(lat_ms)

    # 2. Sandboxed execution
    config["sandbox"]["enabled"] = True
    sandboxed_latencies = []
    logger.info("Running 50 commands with sandbox active...")
    for idx, cmd in enumerate(BENCHMARK_COMMANDS):
        t0 = time.perf_counter()
        res = run_command.invoke({"command": cmd})
        lat_ms = (time.perf_counter() - t0) * 1000.0
        sandboxed_latencies.append(lat_ms)

        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "command_index": idx,
                "command": cmd,
                "unsandboxed_ms": round(unsandboxed_latencies[idx], 2),
                "sandboxed_ms": round(lat_ms, 2),
                "delta_ms": round(lat_ms - unsandboxed_latencies[idx], 2),
            }) + "\n")

    # Metrics aggregation
    u_sorted = sorted(unsandboxed_latencies)
    s_sorted = sorted(sandboxed_latencies)
    total = len(BENCHMARK_COMMANDS)

    u_mean = sum(u_sorted) / total
    s_mean = sum(s_sorted) / total
    u_p50 = u_sorted[int(0.50 * total)]
    s_p50 = s_sorted[int(0.50 * total)]
    u_p95 = u_sorted[int(0.95 * total)]
    s_p95 = s_sorted[int(0.95 * total)]

    overhead_ms = s_mean - u_mean
    overhead_pct = (overhead_ms / u_mean * 100.0) if u_mean else 0.0

    summary = {
        "command_count": total,
        "unsandboxed": {
            "mean_ms": round(u_mean, 2),
            "p50_ms": round(u_p50, 2),
            "p95_ms": round(u_p95, 2),
        },
        "sandboxed": {
            "mean_ms": round(s_mean, 2),
            "p50_ms": round(s_p50, 2),
            "p95_ms": round(s_p95, 2),
        },
        "overhead_delta_mean_ms": round(overhead_ms, 2),
        "overhead_delta_pct": round(overhead_pct, 2),
        "results_file": str(out_file),
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Sandbox Overhead Complete: Unsandboxed Mean={u_mean:.1f}ms, Sandboxed Mean={s_mean:.1f}ms (Overhead: +{overhead_ms:.1f}ms, +{overhead_pct:.1f}%)")
    return summary


if __name__ == "__main__":
    res = run_overhead_benchmark()
    print(json.dumps(res, indent=2))

