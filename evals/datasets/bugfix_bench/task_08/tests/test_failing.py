from src.validator import in_range
def test_max_boundary():
    assert in_range(10, 1, 10) is True, "Upper boundary should be inclusive"
