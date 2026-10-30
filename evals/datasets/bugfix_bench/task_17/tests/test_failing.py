from src.filter import remove_evens
def test_adjacent_evens():
    assert remove_evens([2, 4, 6, 8]) == []
