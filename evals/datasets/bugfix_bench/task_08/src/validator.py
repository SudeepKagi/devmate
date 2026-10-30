def in_range(val, min_val, max_val):
    # BUG: val < max_val excludes max_val
    return min_val <= val < max_val
