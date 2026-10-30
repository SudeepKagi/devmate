from src.stats import calculate_average
def test_empty_list():
    assert calculate_average([]) == 0.0
