from src.stats import calculate_average
def test_normal_list():
    assert calculate_average([10, 20, 30]) == 20.0
