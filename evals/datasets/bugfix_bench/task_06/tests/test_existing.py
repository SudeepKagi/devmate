from src.queue import PriorityQueue
def test_single_item():
    pq = PriorityQueue()
    pq.push("task", 5)
    assert pq.pop() == "task"
