import json
import os
import shutil
from pathlib import Path
import pytest

from devmate.observability.metrics_tracker import (
    MetricsTracker,
    MetricsCallbackHandler,
    calculate_cost,
    extract_token_usage,
    normalize_model_name,
)
from langchain_core.outputs import LLMResult, Generation, ChatGeneration
from langchain_core.messages import AIMessage


@pytest.fixture
def temp_results_dir(tmp_path):
    results_dir = tmp_path / "evals_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    yield str(results_dir)
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_normalize_model_name():
    assert normalize_model_name("gpt-4o-mini-2024-07-18") == "gpt-4o-mini"
    assert normalize_model_name("gpt-4o-2024-08-06") == "gpt-4o"
    assert normalize_model_name("claude-3-5-sonnet-20241022") == "claude-3-5-sonnet"
    assert normalize_model_name("gemini-1.5-flash-latest") == "gemini-1.5-flash"


def test_calculate_cost_exact():
    # gpt-4o-mini: input 0.15/M, cached 0.075/M, output 0.60/M
    # 1,000,000 input uncached + 0 cached + 1,000,000 output = $0.15 + $0.60 = $0.75
    cost, source, eff_date = calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000, 0)
    assert pytest.approx(cost, 1e-6) == 0.75
    assert "https://openai.com/api/pricing/" in source

    # With 500,000 cached tokens on gpt-4o-mini:
    # 500k uncached ($0.075) + 500k cached ($0.0375) + 1M output ($0.60) = $0.7125
    cost_cached, _, _ = calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000, 500_000)
    assert pytest.approx(cost_cached, 1e-6) == 0.7125
    assert cost_cached < cost


def test_extract_token_usage_langchain_standard():
    usage_metadata = {
        "input_tokens": 1500,
        "output_tokens": 250,
        "input_token_details": {"cache_read": 1024},
    }
    inp, out, cached = extract_token_usage(usage_metadata=usage_metadata)
    assert inp == 1500
    assert out == 250
    assert cached == 1024


def test_extract_token_usage_openai_llm_output():
    llm_output = {
        "token_usage": {
            "prompt_tokens": 2048,
            "completion_tokens": 128,
            "total_tokens": 2176,
            "prompt_tokens_details": {"cached_tokens": 1024},
        }
    }
    inp, out, cached = extract_token_usage(llm_output=llm_output)
    assert inp == 2048
    assert out == 128
    assert cached == 1024


def test_extract_token_usage_anthropic():
    response_metadata = {
        "usage": {
            "input_tokens": 3000,
            "output_tokens": 400,
            "cache_read_input_tokens": 2000,
        }
    }
    inp, out, cached = extract_token_usage(response_metadata=response_metadata)
    assert inp == 3000
    assert out == 400
    assert cached == 2000


def test_extract_token_usage_gemini():
    response_metadata = {
        "usage_metadata": {
            "prompt_token_count": 4000,
            "candidates_token_count": 500,
            "cached_content_token_count": 2500,
        }
    }
    inp, out, cached = extract_token_usage(response_metadata=response_metadata)
    assert inp == 4000
    assert out == 500
    assert cached == 2500


def test_metrics_tracker_logging_and_summary(temp_results_dir):
    tracker = MetricsTracker(log_dir=temp_results_dir)

    with tracker.task_context(task_id="task_audit_01", run_id="run_baseline"):
        tracker.record_call(
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=200,
            cached_input_tokens=500,
            latency_ms=350.5,
        )
        tracker.record_call(
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=2000,
            output_tokens=300,
            cached_input_tokens=1000,
            latency_ms=450.0,
        )
        tracker.record_cache_event("task_audit_01", hit=True, domain="test_domain", key="q1")
        tracker.record_router_event("task_audit_01", selected_model="gpt-4o-mini", reason="simple task")

    summary = tracker.get_summary(task_id="task_audit_01", run_id="run_baseline")
    assert summary.call_count == 2
    assert summary.total_input_tokens == 3000
    assert summary.total_output_tokens == 500
    assert summary.total_cached_input_tokens == 1500
    assert summary.total_uncached_input_tokens == 1500
    assert summary.total_tokens == 3500
    assert summary.cache_hits == 1
    assert len(summary.router_decisions) == 1
    assert summary.total_latency_ms == 800.5
    assert summary.avg_latency_ms == pytest.approx(400.25, 0.01)

    # Check JSONL file was written
    main_log = Path(temp_results_dir) / "llm_calls.jsonl"
    task_log = Path(temp_results_dir) / "task_audit_01.jsonl"
    assert main_log.exists()
    assert task_log.exists()

    with open(task_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert len(lines) == 2
    assert lines[0]["task_id"] == "task_audit_01"
    assert lines[0]["cached_input_tokens"] == 500


def test_callback_handler_integration(temp_results_dir):
    tracker = MetricsTracker(log_dir=temp_results_dir)
    handler = MetricsCallbackHandler(tracker=tracker)

    run_id = "test-run-1234"
    handler.on_llm_start(
        serialized={"name": "ChatOpenAI"},
        prompts=["What is 2+2?"],
        run_id=run_id,
        metadata={"ls_provider": "openai", "ls_model_name": "gpt-4o-mini"},
    )

    ai_msg = AIMessage(
        content="4",
        usage_metadata={
            "input_tokens": 50,
            "output_tokens": 10,
            "total_tokens": 60,
            "input_token_details": {"cache_read": 20},
        },
    )
    result = LLMResult(
        generations=[[ChatGeneration(message=ai_msg, text="4")]],
        llm_output={"token_usage": {"prompt_tokens": 50, "completion_tokens": 10}},
    )

    handler.on_llm_end(result, run_id=run_id)

    records = tracker.get_records()
    assert len(records) == 1
    rec = records[0]
    assert rec.model == "gpt-4o-mini"
    assert rec.input_tokens == 50
    assert rec.output_tokens == 10
    assert rec.cached_input_tokens == 20
    assert rec.latency_ms >= 0.0

