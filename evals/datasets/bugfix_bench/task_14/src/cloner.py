BASE_TEMPLATE = {
    "version": "1.0",
    "features": {"logging": True, "auth": True}
}

def create_config(overrides=None):
    # BUG: shallow copy of dict containing nested dict
    conf = BASE_TEMPLATE.copy()
    if overrides:
        conf["features"].update(overrides)
    return conf
