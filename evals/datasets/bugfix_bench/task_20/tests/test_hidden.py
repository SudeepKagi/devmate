from src.stats import calculate_average
def test_hidden_single():
    assert calculate_average([5]) == 5.0
def test_hidden_negative():
    assert calculate_average([-5, 5]) == 0.0
