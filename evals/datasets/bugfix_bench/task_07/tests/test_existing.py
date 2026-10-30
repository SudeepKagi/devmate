import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_cache_hit():
    cache = {"a": "cached_a"}
    assert await get_cached(cache, "a") == "cached_a"
