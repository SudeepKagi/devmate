from src.tax import calculate_tax
def test_hidden_zero():
    assert calculate_tax(0) == 0.0
def test_hidden_cents():
    assert calculate_tax(10.55, 0.05) == 0.53
