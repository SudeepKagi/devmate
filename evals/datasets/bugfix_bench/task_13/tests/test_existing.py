from src.tax import calculate_tax
def test_simple_tax():
    assert calculate_tax(100.0) == 7.0
