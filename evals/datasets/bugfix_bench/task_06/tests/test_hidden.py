from src.queue import PriorityQueue
def test_hidden_multiple():
    pq = PriorityQueue()
    pq.push("mid", 5)
    pq.push("high", 10)
    pq.push("low", 1)
    assert pq.pop() == "high"
    assert pq.pop() == "mid"
    assert pq.pop() == "low"
    assert pq.pop() is None
