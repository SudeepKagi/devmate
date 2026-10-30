from src.tax import calculate_tax
def test_precision_rounding():
    # 19.99 * 0.07 = 1.3993 -> should round to 2 decimals 1.40
    res = calculate_tax(19.99, 0.07)
    assert res == 1.40
