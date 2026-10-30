import json
from datetime import datetime

def serialize_event(data):
    # BUG: doesn't provide custom default serializer
    return json.dumps(data)
