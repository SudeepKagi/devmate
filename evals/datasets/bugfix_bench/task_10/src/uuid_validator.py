import re

UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def is_valid_uuid(s):
    # BUG: re.search without ^ and $ anchors
    return bool(UUID_PATTERN.search(s))
