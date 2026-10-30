from src.pagination import paginate
def test_hidden_second_page():
    items = list(range(20))
    assert paginate(items, page=2, page_size=5) == [5, 6, 7, 8, 9]
def test_hidden_last_page():
    items = list(range(7))
    assert paginate(items, page=2, page_size=5) == [5, 6]
