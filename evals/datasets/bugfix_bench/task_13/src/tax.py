def calculate_tax(subtotal, rate=0.07):
    # BUG: raw float product without round
    return subtotal * rate
