def get_auth_token(headers):
    # BUG: direct indexing without check
    val = headers["Authorization"]
    if val.startswith("Bearer "):
        return val[7:]
    return val
