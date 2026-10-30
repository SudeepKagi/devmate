from src.pagination import paginate
def test_page_size():
    items = list(range(20))
    res = paginate(items, page=1, page_size=5)
    assert len(res) == 5, f"Expected 5 items, got {len(res)}"
