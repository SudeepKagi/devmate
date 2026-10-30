from src.lru import LRUCache
def test_hidden_evict():
    c = LRUCache(2)
    c.put("x", 10)
    c.put("y", 20)
    c.put("z", 30)
    assert c.get("x") is None
    assert c.get("y") == 20
    assert c.get("z") == 30
