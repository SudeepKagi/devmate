import pytest
from devmate.config import config
from devmate.llm.prompt_cache import (
    get_cached_system_prompt,
    is_prompt_caching_enabled,
)


def estimate_token_count(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return int(len(text.split()) * 1.33)


def test_openai_cached_prompt_structure_and_length():
    prompt = get_cached_system_prompt(provider="openai")
    assert isinstance(prompt, str)
    assert "You are Devmate" in prompt
    assert "search_codebase" in prompt
    assert "Devmate Architectural Reference Manual" in prompt

    # Verify that prompt length meets OpenAI's 1,024 token minimum for caching
    token_count = estimate_token_count(prompt)
    assert token_count >= 1024, f"Prompt length ({token_count} tokens) must be >= 1024 tokens for OpenAI cache"


def test_anthropic_cached_prompt_structure():
    prompt = get_cached_system_prompt(provider="anthropic")
    assert isinstance(prompt, list)
    assert len(prompt) == 1
    block = prompt[0]
    assert block["type"] == "text"
    assert "cache_control" in block
    assert block["cache_control"] == {"type": "ephemeral"}
    assert "You are Devmate" in block["text"]


def test_is_prompt_caching_enabled():
    orig = config.get("prompt_caching", {}).get("enabled", False)
    try:
        config["prompt_caching"]["enabled"] = True
        assert is_prompt_caching_enabled() is True
        config["prompt_caching"]["enabled"] = False
        assert is_prompt_caching_enabled() is False
    finally:
        config["prompt_caching"]["enabled"] = orig

