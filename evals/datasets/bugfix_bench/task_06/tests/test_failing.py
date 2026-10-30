from src.queue import PriorityQueue
def test_priority_order():
    pq = PriorityQueue()
    pq.push("low", 1)
    pq.push("high", 10)
    assert pq.pop() == "high"
