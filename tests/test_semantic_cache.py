from unittest.mock import AsyncMock, MagicMock
import pytest
from devmate.cache.semantic_cache import SemanticCache, _cosine_similarity


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert _cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert _cosine_similarity(v1, v3) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_semantic_cache_in_memory_fallback():
    # Use invalid redis port to trigger in-memory fallback
    cache = SemanticCache(redis_url="redis://localhost:9999", threshold=0.85, dims=1536)
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 1536
    mock_embedder.aembed_query = AsyncMock(return_value=[0.1] * 1536)
    cache.embedder = mock_embedder

    await cache.setup()
    assert cache._use_in_memory is True

    # Test put and get
    domain = "test_domain"
    model = "gpt-4o-mini"
    await cache.put("How do I configure logging?", "Use devmate.observability.logger", domain, model)

    # Exact query hit
    hit = await cache.get("How do I configure logging?", domain, model)
    assert hit == "Use devmate.observability.logger"

    # Invalidate
    await cache.invalidate_domain(domain)
    miss = await cache.get("How do I configure logging?", domain, model)
    assert miss is None

