def parse_port(params, default=8000):
    val = params.get("port")
    if val is None:
        return default
    # BUG: forgets to cast str to int
    return val
