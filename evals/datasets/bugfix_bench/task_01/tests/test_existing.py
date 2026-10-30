from src.pagination import paginate
def test_empty():
    assert paginate([], 1, 5) == []
def test_invalid_page():
    assert paginate([1, 2, 3], 0, 5) == []
