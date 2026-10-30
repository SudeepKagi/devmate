from src.filter import remove_evens
def test_hidden_odds():
    assert remove_evens([1, 3, 5]) == [1, 3, 5]
def test_hidden_mixed():
    assert remove_evens([1, 2, 2, 3, 4, 4, 5]) == [1, 3, 5]
