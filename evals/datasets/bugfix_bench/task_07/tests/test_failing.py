import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_cache_miss_resolved():
    cache = {}
    val = await get_cached(cache, "b")
    assert isinstance(val, str), f"Expected str, got {type(val)}"
    assert val == "data_for_b"
