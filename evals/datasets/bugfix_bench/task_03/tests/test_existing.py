from src.discounts import calculate_discount
def test_small_total():
    assert calculate_discount(50) == 0.0
def test_large_total():
    assert calculate_discount(200) == 20.0
