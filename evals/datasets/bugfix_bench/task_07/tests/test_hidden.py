import pytest
from src.async_cache import get_cached

@pytest.mark.asyncio
async def test_hidden_cache_population():
    cache = {}
    val1 = await get_cached(cache, "c")
    assert val1 == "data_for_c"
    assert cache["c"] == "data_for_c"
