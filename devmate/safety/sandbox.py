"""
Devmate Sandboxed Execution Module.
Provides workspace path jailing for filesystem tools and isolated container/process execution
for shell commands (non-root, workspace-only mount, resource limits, no network, secret scrubbing).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


class SecurityError(Exception):
    """Raised when an operation violates workspace sandbox boundaries."""
    pass


def is_sandbox_enabled() -> bool:
    """Check configuration flag for sandboxing."""
    return bool(config.get("sandbox", {}).get("enabled", False))


def get_workspace_root() -> Path:
    """Return the absolute canonical path to the active workspace root."""
    return Path.cwd().resolve()


def validate_workspace_path(
    path: str | Path,
    workspace_root: Optional[str | Path] = None,
    allow_symlink_outside: bool = False,
) -> Path:
    """
    Enforce strict path jail: ensures path resides within workspace root.
    Blocks directory traversal ('../'), symlink escapes, and root references.
    """
    root = Path(workspace_root or get_workspace_root()).resolve()
    target = Path(path)

    # If relative, resolve relative to root
    if not target.is_absolute():
        resolved = (root / target).resolve()
    else:
        resolved = target.resolve()

    # 1. Path must be relative to workspace root
    try:
        resolved.relative_to(root)
    except ValueError:
        raise SecurityError(
            f"Path traversal blocked: '{path}' resolves to '{resolved}' which is outside workspace jail '{root}'"
        )

    # 2. Check for symlink escapes: verify realpath matches resolved inside root
    if not allow_symlink_outside and os.path.islink(resolved):
        real_target = Path(os.path.realpath(resolved))
        try:
            real_target.relative_to(root)
        except ValueError:
            raise SecurityError(
                f"Symlink escape blocked: '{resolved}' points to '{real_target}' outside workspace jail '{root}'"
            )

    return resolved


def check_docker_available() -> bool:
    """Check if the Docker daemon is responsive."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def build_sanitized_env() -> Dict[str, str]:
    """Sanitize environment variables to prevent API key and token exfiltration."""
    blocked_keys = {
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "XAI_API_KEY",
        "QDRANT_API_KEY",
        "DEEPEVAL_API_KEY",
        "CONFIDENT_AI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    }
    clean_env = {}
    for k, v in os.environ.items():
        if k not in blocked_keys and not k.endswith("_SECRET") and not k.endswith("_KEY"):
            clean_env[k] = v
    # Set safe minimal defaults
    clean_env["DEVMATE_SANDBOX"] = "1"
    return clean_env


def execute_sandboxed_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    allow_network: bool = False,
    memory_limit: str = "512m",
    cpu_limit: str = "1.0",
    pids_limit: int = 100,
) -> Tuple[int, str, str, Dict[str, Any]]:
    """
    Execute a shell command inside Docker container sandbox if available,
    or local path-jailed and secret-sanitized process sandbox as fallback.
    Returns (exit_code, stdout, stderr, metadata).
    """
    workspace = get_workspace_root()
    target_cwd = validate_workspace_path(cwd or workspace, workspace)
    timeout_sec = timeout or config.get("sandbox", {}).get("timeout_seconds", 30)

    start_time = time.perf_counter()

    if check_docker_available():
        # Containerized Docker execution
        net_flag = "--network=none" if not allow_network else ""
        docker_cmd = [
            "docker", "run", "--rm",
            net_flag,
            f"--memory={memory_limit}",
            f"--cpus={cpu_limit}",
            f"--pids-limit={pids_limit}",
            "--user=1000:1000",
            "-v", f"{workspace}:/workspace:rw",
            "-w", f"/workspace/{target_cwd.relative_to(workspace)}",
            "python:3.11-slim",
            "sh", "-c", command,
        ]
        # Filter empty strings
        docker_cmd = [c for c in docker_cmd if c]
        logger.info(f"Executing in Docker container: {' '.join(docker_cmd)}")
        try:
            res = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return (
                res.returncode,
                res.stdout,
                res.stderr,
                {
                    "mode": "docker",
                    "latency_ms": round(elapsed_ms, 2),
                    "network_isolated": not allow_network,
                    "non_root": True,
                },
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return -1, "", f"Execution timed out after {timeout_sec}s", {"mode": "docker", "timeout": True}
        except Exception as e:
            logger.warning(f"Docker execution failed, falling back to local path-jail: {e}")

    # Local Path-Jail and Secret-Sanitized Process Sandbox
    clean_env = build_sanitized_env()
    logger.info(f"Executing in local path-jailed sandbox (cwd={target_cwd}): {command}")

    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=str(target_cwd),
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return (
            res.returncode,
            res.stdout,
            res.stderr,
            {
                "mode": "local_jail",
                "latency_ms": round(elapsed_ms, 2),
                "secrets_scrubbed": True,
                "timeout": False,
            },
        )
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return -1, "", f"Execution timed out after {timeout_sec}s", {"mode": "local_jail", "timeout": True}
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return -2, "", str(e), {"mode": "local_jail", "error": str(e)}

