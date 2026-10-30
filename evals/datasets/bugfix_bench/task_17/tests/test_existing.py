from src.filter import remove_evens
def test_single():
    assert remove_evens([1, 2, 3]) == [1, 3]
