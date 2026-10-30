from src.buffer import CircularBuffer
def test_hidden_multiple_wraps():
    b = CircularBuffer(2)
    b.append("a")
    b.append("b")
    b.append("c")
    assert b.get_all() == ["b", "c"]
