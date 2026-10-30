from src.discounts import calculate_discount
def test_hidden_zero():
    assert calculate_discount(0) == 0.0
def test_hidden_fraction():
    assert calculate_discount(99.99) == 0.0
    assert calculate_discount(100.01) == pytest.approx(10.001)
import pytest
