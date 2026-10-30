from src.discounts import calculate_discount
def test_boundary_tier():
    assert calculate_discount(100) == 10.0, "Total of 100 should qualify for 10% discount"
