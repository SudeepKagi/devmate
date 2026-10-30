"""
Devmate Dynamic Model Router.
Intelligently routes LLM invocations between low-cost fast models (gpt-4o-mini)
and reasoning-intensive strong models (gpt-4o) using transparent complexity rules
and automated failure escalation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from devmate.config import config
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import metrics_tracker
from devmate.llm.factory import get_llm

logger = get_logger(__name__)

# Keywords signaling high-complexity cognitive reasoning or multi-file code generation
COMPLEX_KEYWORDS = {
    "fix",
    "debug",
    "patch",
    "refactor",
    "architect",
    "architecture",
    "implement",
    "regression",
    "failing",
    "segfault",
    "deadlock",
    "race condition",
    "memory leak",
    "dag",
    "multi-file",
    "security vulnerability",
}

# Keywords signaling low-complexity queries (search, lookup, syntax explanation, formatting)
SIMPLE_KEYWORDS = {
    "what is",
    "where is",
    "find",
    "search",
    "how to run",
    "explain",
    "list",
    "format",
    "docstring",
    "comment",
}


class ModelRouter:
    """Rule-based and escalation-aware LLM router."""

    def __init__(self):
        self.fast_model = config.get("router", {}).get("fast_model", "gpt-4o-mini")
        self.strong_model = config.get("router", {}).get("strong_model", "gpt-4o")

    def is_enabled(self) -> bool:
        """Check if router is active in configuration."""
        return bool(config.get("router", {}).get("enabled", False))

    def route(
        self,
        task_type: str = "query",
        query: str = "",
        task_id: str = "default",
        previous_error: Optional[str] = None,
        tool_error_count: int = 0,
        complexity_score: Optional[float] = None,
    ) -> Tuple[str, str, bool]:
        """
        Determine model to use based on rules, complexity, and escalation state.
        Returns: (selected_model, reason, escalated)
        """
        if not self.is_enabled():
            model = config.get("llm", {}).get("model", self.strong_model)
            return model, "router_disabled_use_config_model", False

        # Escalation Rule 1: Prior error or tool failure escalates immediately to strong model
        if previous_error or tool_error_count > 0:
            reason = f"escalation_error_detected (err={previous_error}, tools_failed={tool_error_count})"
            metrics_tracker.record_router_event(
                task_id=task_id,
                selected_model=self.strong_model,
                reason=reason,
                escalated=True,
            )
            logger.info(f"Model Router ESCALATED to {self.strong_model}: {reason}")
            return self.strong_model, reason, True

        # Rule 2: Task-type classification
        if task_type in ("planning", "architecture", "debugging", "bugfix"):
            reason = f"high_complexity_task_type ({task_type})"
            metrics_tracker.record_router_event(
                task_id=task_id,
                selected_model=self.strong_model,
                reason=reason,
                escalated=False,
            )
            logger.info(f"Model Router selected {self.strong_model}: {reason}")
            return self.strong_model, reason, False

        if task_type in ("summarization", "search_reformulation", "formatting", "docstring"):
            reason = f"lightweight_task_type ({task_type})"
            metrics_tracker.record_router_event(
                task_id=task_id,
                selected_model=self.fast_model,
                reason=reason,
                escalated=False,
            )
            logger.info(f"Model Router selected {self.fast_model}: {reason}")
            return self.fast_model, reason, False

        # Rule 3: Text content inspection
        q_lower = query.lower()

        # Check for complex keywords
        for kw in COMPLEX_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                reason = f"complex_keyword_matched ('{kw}')"
                metrics_tracker.record_router_event(
                    task_id=task_id,
                    selected_model=self.strong_model,
                    reason=reason,
                    escalated=False,
                )
                logger.info(f"Model Router selected {self.strong_model}: {reason}")
                return self.strong_model, reason, False

        # Rule 4: Long queries (> 150 words) imply multi-faceted requests
        word_count = len(query.split())
        if word_count > 150:
            reason = f"query_length_high ({word_count} words)"
            metrics_tracker.record_router_event(
                task_id=task_id,
                selected_model=self.strong_model,
                reason=reason,
                escalated=False,
            )
            logger.info(f"Model Router selected {self.strong_model}: {reason}")
            return self.strong_model, reason, False

        # Rule 5: Default read-only, informational, or short queries go to fast model
        reason = "standard_lookup_default_light"
        metrics_tracker.record_router_event(
            task_id=task_id,
            selected_model=self.fast_model,
            reason=reason,
            escalated=False,
        )
        logger.info(f"Model Router selected {self.fast_model}: {reason}")
        return self.fast_model, reason, False


# Global router singleton
router = ModelRouter()


def get_routed_llm(
    task_type: str = "query",
    query: str = "",
    task_id: str = "default",
    previous_error: Optional[str] = None,
    tool_error_count: int = 0,
    temperature: Optional[float] = None,
):
    """Factory helper returning configured LangChain LLM for the routed model."""
    selected_model, reason, escalated = router.route(
        task_type=task_type,
        query=query,
        task_id=task_id,
        previous_error=previous_error,
        tool_error_count=tool_error_count,
    )
    return get_llm(model=selected_model, temperature=temperature)

