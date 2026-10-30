import pytest
from devmate.config import config
from devmate.llm.router import ModelRouter, router
from devmate.observability.metrics_tracker import metrics_tracker


def test_router_disabled_fallback():
    orig = config.get("router", {}).get("enabled", False)
    orig_model = config.get("llm", {}).get("model", "gpt-4o-mini")
    try:
        config["router"]["enabled"] = False
        config["llm"]["model"] = "gpt-4o-mini"
        r = ModelRouter()
        model, reason, escalated = r.route(task_type="bugfix", query="fix this critical error")
        assert model == "gpt-4o-mini"
        assert "router_disabled" in reason
        assert escalated is False
    finally:
        config["router"]["enabled"] = orig
        config["llm"]["model"] = orig_model


def test_router_escalation_on_error():
    orig = config.get("router", {}).get("enabled", False)
    try:
        config["router"]["enabled"] = True
        r = ModelRouter()
        # With previous error, should escalate to strong_model even for simple query
        model, reason, escalated = r.route(
            task_type="query",
            query="where is main.py",
            previous_error="ToolExecutionError: command failed",
        )
        assert model == r.strong_model
        assert escalated is True
        assert "escalation_error_detected" in reason

        # With tool error count > 0, should also escalate
        model, reason, escalated = r.route(
            task_type="query",
            query="simple lookup",
            tool_error_count=2,
        )
        assert model == r.strong_model
        assert escalated is True
    finally:
        config["router"]["enabled"] = orig


def test_router_task_type_and_keyword_rules():
    orig = config.get("router", {}).get("enabled", False)
    try:
        config["router"]["enabled"] = True
        r = ModelRouter()

        # Complex task type -> strong model
        model, reason, escalated = r.route(task_type="planning", query="build an app")
        assert model == r.strong_model
        assert escalated is False

        # Lightweight task type -> fast model
        model, reason, escalated = r.route(task_type="summarization", query="summarize notes")
        assert model == r.fast_model
        assert escalated is False

        # Complex keyword in query -> strong model
        model, reason, escalated = r.route(task_type="query", query="Please fix the race condition in the cache")
        assert model == r.strong_model
        assert "complex_keyword_matched" in reason

        # Simple lookup query -> fast model
        model, reason, escalated = r.route(task_type="query", query="What is the port number for Redis?")
        assert model == r.fast_model
        assert "standard_lookup" in reason
    finally:
        config["router"]["enabled"] = orig

