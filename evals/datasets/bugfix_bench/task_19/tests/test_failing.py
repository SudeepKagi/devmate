from datetime import datetime
from src.serializer import serialize_event
def test_datetime_serialization():
    dt = datetime(2026, 1, 1, 12, 0, 0)
    res = serialize_event({"timestamp": dt})
    assert "2026-01-01" in res
