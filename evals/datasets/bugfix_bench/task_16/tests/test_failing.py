from src.buffer import CircularBuffer
def test_wrapped_order():
    b = CircularBuffer(3)
    b.append(1)
    b.append(2)
    b.append(3)
    b.append(4)  # overwrites 1, buffer now [4, 2, 3], write_idx=1 -> oldest is 2
    assert b.get_all() == [2, 3, 4]
