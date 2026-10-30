from datetime import date
from src.serializer import serialize_event
def test_hidden_date():
    res = serialize_event({"day": date(2026, 5, 10)})
    assert "2026-05-10" in res
