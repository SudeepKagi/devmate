from src.lru import LRUCache
def test_access_updates_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")  # "a" accessed, so "b" is now oldest
    c.put("c", 3)  # should evict "b", keeping "a" and "c"
    assert c.get("b") is None
    assert c.get("a") == 1
