from src.buffer import CircularBuffer
def test_partial():
    b = CircularBuffer(3)
    b.append(1)
    b.append(2)
    assert b.get_all() == [1, 2]
