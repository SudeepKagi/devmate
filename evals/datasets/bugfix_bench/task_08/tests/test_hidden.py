from src.validator import in_range
def test_hidden_min_boundary():
    assert in_range(1, 1, 10) is True
def test_hidden_above():
    assert in_range(11, 1, 10) is False
