import asyncio

async def fetch_data(key):
    await asyncio.sleep(0.01)
    return f"data_for_{key}"

async def get_cached(cache, key):
    if key in cache:
        return cache[key]
    val = fetch_data(key)  # BUG: missing await
    cache[key] = val
    return val
