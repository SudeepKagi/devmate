from src.validator import in_range
def test_middle():
    assert in_range(5, 1, 10) is True
def test_below():
    assert in_range(0, 1, 10) is False
