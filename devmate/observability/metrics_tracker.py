from __future__ import annotations

import json
import os
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    # Graceful fallback if langchain_core is missing in standalone tests
    class BaseCallbackHandler:  # type: ignore
        pass

    class LLMResult:  # type: ignore
        pass

from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

# Context variables for tracking asynchronous task execution
_CURRENT_TASK_ID: ContextVar[str] = ContextVar("current_task_id", default="default")
_CURRENT_RUN_ID: ContextVar[str] = ContextVar("current_run_id", default="run_1")
_CURRENT_STEP_INDEX: ContextVar[int] = ContextVar("current_step_index", default=0)


class LLMCallRecord(BaseModel):
    """Grounded metrics record for a single LLM invocation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    task_id: str = "default"
    run_id: str = "run_1"
    step_index: int = 0
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    uncached_input_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cache_hit: bool = False
    router_decision: Optional[Dict[str, Any]] = None
    estimated_cost_usd: float = 0.0
    pricing_source: str = ""
    pricing_date: str = ""
    error: Optional[str] = None


class TaskMetricsSummary(BaseModel):
    """Aggregated empirical metrics for a task or benchmark execution."""
    task_id: str
    run_id: str
    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_input_tokens: int = 0
    total_uncached_input_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    router_decisions: List[Dict[str, Any]] = Field(default_factory=list)


def normalize_model_name(model_name: str) -> str:
    """Normalize specific snapshot model strings to pricing keys."""
    m = model_name.lower().strip()
    if "gpt-4o-mini" in m:
        return "gpt-4o-mini"
    if "gpt-4o" in m:
        return "gpt-4o"
    if "claude-3-5-sonnet" in m or "claude-3.5-sonnet" in m:
        return "claude-3-5-sonnet"
    if "claude-3-5-haiku" in m or "claude-3.5-haiku" in m:
        return "claude-3-5-haiku"
    if "gemini-1.5-flash" in m:
        return "gemini-1.5-flash"
    if "gemini-1.5-pro" in m:
        return "gemini-1.5-pro"
    if "text-embedding-3-small" in m:
        return "text-embedding-3-small"
    return m


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> tuple[float, str, str]:
    """
    Calculate estimated cost in USD based on official pricing table in config.
    Returns (cost_usd, source_url, effective_date).
    """
    pricing_conf = config.get("pricing", {})
    source_url = pricing_conf.get("source_url", "https://openai.com/api/pricing/")
    effective_date = pricing_conf.get("effective_date", "2024-10-01")
    models = pricing_conf.get("models", {})

    key = normalize_model_name(model_name)
    model_rates = models.get(key)
    if not model_rates:
        # Fallback to gpt-4o-mini pricing if unspecified
        model_rates = models.get(
            "gpt-4o-mini",
            {
                "input_per_million": 0.15,
                "cached_input_per_million": 0.075,
                "output_per_million": 0.60,
            },
        )

    cached_tokens = max(0, min(cached_input_tokens, input_tokens))
    uncached_tokens = max(0, input_tokens - cached_tokens)

    input_rate = float(model_rates.get("input_per_million", 0.15))
    cached_rate = float(model_rates.get("cached_input_per_million", input_rate * 0.5))
    output_rate = float(model_rates.get("output_per_million", 0.60))

    cost = (
        (uncached_tokens * input_rate)
        + (cached_tokens * cached_rate)
        + (output_tokens * output_rate)
    ) / 1_000_000.0

    return round(cost, 8), source_url, effective_date


def extract_token_usage(
    llm_output: Optional[dict] = None,
    usage_metadata: Optional[dict] = None,
    response_metadata: Optional[dict] = None,
) -> tuple[int, int, int]:
    """
    Robustly extract (input_tokens, output_tokens, cached_input_tokens)
    from LangChain 0.3+ usage structures, supporting OpenAI, Anthropic, and Gemini.
    """
    input_tokens = 0
    output_tokens = 0
    cached_input_tokens = 0

    # 1. Check standardized LangChain usage_metadata
    if usage_metadata and isinstance(usage_metadata, dict):
        input_tokens = usage_metadata.get("input_tokens", 0) or usage_metadata.get("prompt_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0) or usage_metadata.get("completion_tokens", 0)
        details = usage_metadata.get("input_token_details") or {}
        if isinstance(details, dict):
            cached_input_tokens = details.get("cache_read", 0) or details.get("cached_tokens", 0)

    # 2. Check OpenAI / standard llm_output token_usage
    if llm_output and isinstance(llm_output, dict):
        token_usage = llm_output.get("token_usage") or {}
        if isinstance(token_usage, dict):
            if not input_tokens:
                input_tokens = token_usage.get("prompt_tokens", 0)
            if not output_tokens:
                output_tokens = token_usage.get("completion_tokens", 0)
            details = token_usage.get("prompt_tokens_details") or {}
            if isinstance(details, dict) and not cached_input_tokens:
                cached_input_tokens = details.get("cached_tokens", 0)

    # 3. Check response_metadata for provider specifics (OpenAI, Anthropic, Gemini)
    if response_metadata and isinstance(response_metadata, dict):
        # OpenAI style in response_metadata
        token_usage = response_metadata.get("token_usage") or {}
        if isinstance(token_usage, dict):
            if not input_tokens:
                input_tokens = token_usage.get("prompt_tokens", 0)
            if not output_tokens:
                output_tokens = token_usage.get("completion_tokens", 0)
            details = token_usage.get("prompt_tokens_details") or {}
            if isinstance(details, dict) and not cached_input_tokens:
                cached_input_tokens = details.get("cached_tokens", 0)

        # Anthropic style in response_metadata: usage: {input_tokens, output_tokens, cache_read_input_tokens}
        anthropic_usage = response_metadata.get("usage") or {}
        if isinstance(anthropic_usage, dict):
            if not input_tokens:
                input_tokens = anthropic_usage.get("input_tokens", 0)
            if not output_tokens:
                output_tokens = anthropic_usage.get("output_tokens", 0)
            if not cached_input_tokens:
                cached_input_tokens = anthropic_usage.get("cache_read_input_tokens", 0)

        # Gemini style in response_metadata
        gemini_usage = response_metadata.get("usage_metadata") or {}
        if isinstance(gemini_usage, dict):
            if not input_tokens:
                input_tokens = (
                    gemini_usage.get("prompt_token_count", 0)
                    or gemini_usage.get("input_tokens", 0)
                )
            if not output_tokens:
                output_tokens = (
                    gemini_usage.get("candidates_token_count", 0)
                    or gemini_usage.get("output_tokens", 0)
                )
            if not cached_input_tokens:
                cached_input_tokens = gemini_usage.get("cached_content_token_count", 0)

    cached_input_tokens = max(0, min(cached_input_tokens, input_tokens))
    return int(input_tokens), int(output_tokens), int(cached_input_tokens)


class TaskContextManager:
    """Context manager for scoping LLM calls to a specific task and run."""
    def __init__(self, task_id: str, run_id: str = "run_1", step_index: int = 0):
        self.task_id = task_id
        self.run_id = run_id
        self.step_index = step_index
        self._tokens: list[Any] = []

    def __enter__(self):
        self._tokens.append(_CURRENT_TASK_ID.set(self.task_id))
        self._tokens.append(_CURRENT_RUN_ID.set(self.run_id))
        self._tokens.append(_CURRENT_STEP_INDEX.set(self.step_index))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if len(self._tokens) >= 3:
            _CURRENT_STEP_INDEX.reset(self._tokens[2])
            _CURRENT_RUN_ID.reset(self._tokens[1])
            _CURRENT_TASK_ID.reset(self._tokens[0])


class MetricsTracker:
    """
    Thread-safe empirical metrics tracker for Devmate LLM calls and evaluation runs.
    Logs each invocation to evals/results/ as JSONL.
    """
    def __init__(self, log_dir: str = "evals/results"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.main_log_file = self.log_dir / "llm_calls.jsonl"
        self._lock = threading.Lock()
        self._records: List[LLMCallRecord] = []
        self._cache_events: List[Dict[str, Any]] = []
        self._router_events: List[Dict[str, Any]] = []

    def task_context(self, task_id: str, run_id: str = "run_1", step_index: int = 0) -> TaskContextManager:
        """Create a scoped context for tracking a task."""
        return TaskContextManager(task_id=task_id, run_id=run_id, step_index=step_index)

    def record_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
        latency_ms: float = 0.0,
        cache_hit: bool = False,
        router_decision: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_index: Optional[int] = None,
        error: Optional[str] = None,
    ) -> LLMCallRecord:
        """Record an LLM call, calculate exact cost, append to memory and JSONL."""
        t_id = task_id or _CURRENT_TASK_ID.get()
        r_id = run_id or _CURRENT_RUN_ID.get()
        s_idx = step_index if step_index is not None else _CURRENT_STEP_INDEX.get()

        cached_tokens = max(0, min(cached_input_tokens, input_tokens))
        uncached_tokens = max(0, input_tokens - cached_tokens)
        total_tokens = input_tokens + output_tokens

        cost, source_url, effective_date = calculate_cost(
            model_name=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )

        record = LLMCallRecord(
            task_id=t_id,
            run_id=r_id,
            step_index=s_idx,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            uncached_input_tokens=uncached_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cache_hit=cache_hit,
            router_decision=router_decision,
            estimated_cost_usd=cost,
            pricing_source=source_url,
            pricing_date=effective_date,
            error=error,
        )

        with self._lock:
            self._records.append(record)
            self._write_jsonl(record)

        return record

    def record_cache_event(self, task_id: str, hit: bool, domain: str, key: str) -> None:
        """Record semantic cache lookup event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "hit": hit,
            "domain": domain,
            "key": key,
        }
        with self._lock:
            self._cache_events.append(event)

    def record_router_event(
        self,
        task_id: str,
        selected_model: str,
        reason: str,
        escalated: bool = False,
    ) -> Dict[str, Any]:
        """Record router decision event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "selected_model": selected_model,
            "reason": reason,
            "escalated": escalated,
        }
        with self._lock:
            self._router_events.append(event)
        return event

    def _write_jsonl(self, record: LLMCallRecord) -> None:
        """Write record to global and per-task JSONL files."""
        try:
            line = record.model_dump_json() + "\n"
            # Global log
            with open(self.main_log_file, "a", encoding="utf-8") as f:
                f.write(line)

            # Per-task log if task_id is specified
            if record.task_id and record.task_id != "default":
                task_file = self.log_dir / f"{record.task_id}.jsonl"
                with open(task_file, "a", encoding="utf-8") as f:
                    f.write(line)
        except Exception as e:
            logger.error(f"Failed to write metrics record to JSONL: {e}")

    def get_records(
        self, task_id: Optional[str] = None, run_id: Optional[str] = None
    ) -> List[LLMCallRecord]:
        """Get in-memory records matching filters."""
        with self._lock:
            res = list(self._records)
        if task_id:
            res = [r for r in res if r.task_id == task_id]
        if run_id:
            res = [r for r in res if r.run_id == run_id]
        return res

    def get_summary(
        self, task_id: str = "default", run_id: str = "run_1"
    ) -> TaskMetricsSummary:
        """Compute summary statistics for a given task/run."""
        records = self.get_records(task_id=task_id, run_id=run_id)
        if not records:
            return TaskMetricsSummary(task_id=task_id, run_id=run_id)

        call_count = len(records)
        total_inp = sum(r.input_tokens for r in records)
        total_out = sum(r.output_tokens for r in records)
        total_cached = sum(r.cached_input_tokens for r in records)
        total_uncached = sum(r.uncached_input_tokens for r in records)
        total_tok = sum(r.total_tokens for r in records)
        total_cost = sum(r.estimated_cost_usd for r in records)
        latencies = [r.latency_ms for r in records]
        total_lat = sum(latencies)
        avg_lat = total_lat / call_count if call_count else 0.0

        sorted_lat = sorted(latencies)
        p50 = sorted_lat[int(0.50 * len(sorted_lat))] if sorted_lat else 0.0
        p95 = sorted_lat[int(0.95 * len(sorted_lat))] if sorted_lat else 0.0

        hits = sum(1 for e in self._cache_events if e.get("task_id") == task_id and e.get("hit"))
        misses = sum(1 for e in self._cache_events if e.get("task_id") == task_id and not e.get("hit"))
        r_events = [e for e in self._router_events if e.get("task_id") == task_id]

        return TaskMetricsSummary(
            task_id=task_id,
            run_id=run_id,
            call_count=call_count,
            total_input_tokens=total_inp,
            total_output_tokens=total_out,
            total_cached_input_tokens=total_cached,
            total_uncached_input_tokens=total_uncached,
            total_tokens=total_tok,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(total_lat, 2),
            avg_latency_ms=round(avg_lat, 2),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            cache_hits=hits,
            cache_misses=misses,
            router_decisions=r_events,
        )

    def reset(self) -> None:
        """Reset in-memory records and events."""
        with self._lock:
            self._records.clear()
            self._cache_events.clear()
            self._router_events.clear()


# Global tracker instance
metrics_tracker = MetricsTracker()


class MetricsCallbackHandler(BaseCallbackHandler):
    """
    LangChain Callback Handler that intercepts every LLM invocation,
    measures latency, extracts usage metadata including cache tokens,
    and logs the call via MetricsTracker.
    """
    def __init__(self, tracker: Optional[MetricsTracker] = None):
        super().__init__()
        self.tracker = tracker or metrics_tracker
        self._starts: Dict[str, tuple[float, str, str]] = {}
        self._lock = threading.Lock()

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        start_time = time.perf_counter()
        meta = metadata or {}
        model = (
            meta.get("ls_model_name")
            or kwargs.get("invocation_params", {}).get("model")
            or kwargs.get("invocation_params", {}).get("model_name")
            or serialized.get("name")
            or config.get("llm", {}).get("model", "gpt-4o-mini")
        )
        provider = (
            meta.get("ls_provider")
            or config.get("llm", {}).get("provider", "openai")
        )
        with self._lock:
            self._starts[str(run_id)] = (start_time, str(provider), str(model))

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self.on_llm_start(
            serialized,
            [],
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            metadata=metadata,
            **kwargs,
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        end_time = time.perf_counter()
        key = str(run_id)
        with self._lock:
            start_info = self._starts.pop(key, None)

        if start_info:
            start_time, provider, model = start_info
            latency_ms = (end_time - start_time) * 1000.0
        else:
            latency_ms = 0.0
            provider = config.get("llm", {}).get("provider", "openai")
            model = config.get("llm", {}).get("model", "gpt-4o-mini")

        # Extract usage metadata
        usage_meta = None
        resp_meta = None
        if hasattr(response, "generations") and response.generations:
            gen_list = response.generations[0]
            if gen_list:
                gen = gen_list[0]
                msg = getattr(gen, "message", None)
                if msg:
                    usage_meta = getattr(msg, "usage_metadata", None)
                    resp_meta = getattr(msg, "response_metadata", None)

        llm_out = getattr(response, "llm_output", None)
        inp, out, cached = extract_token_usage(
            llm_output=llm_out,
            usage_metadata=usage_meta,
            response_metadata=resp_meta,
        )

        self.tracker.record_call(
            provider=provider,
            model=model,
            input_tokens=inp,
            output_tokens=out,
            cached_input_tokens=cached,
            latency_ms=latency_ms,
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        end_time = time.perf_counter()
        key = str(run_id)
        with self._lock:
            start_info = self._starts.pop(key, None)

        if start_info:
            start_time, provider, model = start_info
            latency_ms = (end_time - start_time) * 1000.0
        else:
            latency_ms = 0.0
            provider = config.get("llm", {}).get("provider", "openai")
            model = config.get("llm", {}).get("model", "gpt-4o-mini")

        self.tracker.record_call(
            provider=provider,
            model=model,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            latency_ms=latency_ms,
            error=str(error),
        )

