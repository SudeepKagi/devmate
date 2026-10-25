from __future__ import annotations

import os
from typing import Any
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    PIIDetectionError,
    PIIMiddleware,
    hook_config,
)
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime
from rich.console import Console
from devmate.observability.logger import get_logger

logger = get_logger(__name__)
console = Console()

PASSWORD_SHARE_PATTERN = (
    r"(?i)\b(?:my\s+)?(?:password|passwrod|passwd|pwd)\s*(?:is|=|:)\s*\S+"
)
PASSWORD_IN_RESPONSE_PATTERN = (
    r'(?i)(?:password|passwrod|passwd|pwd)\s*["\']?[\w!@#$%^&*.-]{3,}["\']?'
)
API_KEY_SHARE_PATTERN = r"(?i)\b(?:api[_\s-]?key|apikey)\s*(?:is|=|:)\s*\S+"


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a truthy env var string ('1'/'true'/'yes'/'on') into a bool."""
    val = os.getenv(name, str(default)).strip().lower()
    return val in {"1", "true", "yes", "on"}


class ContentFilterMiddleware(AgentMiddleware):
    """Deterministic guardrail: block banned keywords before the agent runs."""

    def __init__(self, banned_keywords: list[str]):
        super().__init__()
        self.banned_keywords = [k.lower() for k in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state.get("messages"):
            return None

        # Find the most recent human message
        latest_user_message = None
        for message in reversed(state["messages"]):
            if getattr(message, "type", None) == "human":
                latest_user_message = message
                break

        if latest_user_message is None:
            return None

        content = str(latest_user_message.content).lower()
        for keyword in self.banned_keywords:
            if keyword in content:
                logger.warning(f"ContentFilter triggered on banned keyword: {keyword}")
                return {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": (
                                "I cannot process requests containing inappropriate content. "
                                "Please rephrase your request."
                            ),
                        }
                    ],
                    "jump_to": "end",
                }
        return None


class RedactionDebugMiddleware(AgentMiddleware):
    """Print sanitized user input after PII middleware runs."""

    def __init__(self, enabled: bool):
        super().__init__()
        self.enabled = enabled

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not self.enabled or not state.get("messages"):
            return None

        for message in reversed(state["messages"]):
            if getattr(message, "type", None) == "human":
                console.print(f"[dim yellow][Guardrail Debug] Input sent to model: {message.content}[/dim yellow]")
                break
        return None


class SafetyGuardrailMiddleware(AgentMiddleware):
    """Model-based guardrail: check final response safety after the agent completes."""

    def __init__(self, safety_model):
        super().__init__()
        self.safety_model = safety_model

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state.get("messages"):
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        safety_prompt = (
            "Evaluate if this response is safe and appropriate for a demo assistant. "
            "Mark UNSAFE if the response repeats, quotes, or analyzes a user-provided "
            "password, secret, API key, or credential. Respond with only SAFE or UNSAFE.\n\n"
            f"Response: {last_message.content}"
        )

        try:
            result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])
            content_str = str(getattr(result, "content", result)).upper()
            if "UNSAFE" in content_str:
                logger.warning("SafetyGuardrail marked response as UNSAFE")
                last_message.content = "I cannot provide that response. Please rephrase your request."
        except Exception as e:
            logger.error(f"SafetyGuardrail judge error: {e}")

        return None


def build_guardrails(safety_model=None, show_redacted_input: bool = False) -> list:
    """Build list of guardrail middlewares in strict order."""
    middleware = [
        ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware", "ransomware"]),
        PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True),
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
            apply_to_output=True,
        ),
        PIIMiddleware(
            "api_key_share",
            detector=API_KEY_SHARE_PATTERN,
            strategy="redact",
            apply_to_input=True,
            apply_to_output=True,
        ),
        PIIMiddleware(
            "openai_api_key",
            detector=r"sk-[a-zA-Z0-9]{20,}",
            strategy="block",
            apply_to_input=True,
        ),
        PIIMiddleware(
            "password_share",
            detector=PASSWORD_SHARE_PATTERN,
            strategy="redact",
            apply_to_input=True,
            apply_to_output=True,
        ),
        PIIMiddleware(
            "password_output",
            detector=PASSWORD_IN_RESPONSE_PATTERN,
            strategy="redact",
            apply_to_output=True,
            apply_to_tool_results=True,
        ),
        RedactionDebugMiddleware(enabled=show_redacted_input),
    ]

    if safety_model is not None:
        middleware.append(SafetyGuardrailMiddleware(safety_model))

    return middleware
