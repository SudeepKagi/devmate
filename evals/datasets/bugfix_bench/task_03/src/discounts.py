def calculate_discount(total):
    if total > 100:  # BUG: should be >= 100
        return total * 0.10
    return 0.0
