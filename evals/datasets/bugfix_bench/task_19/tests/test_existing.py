from src.serializer import serialize_event
def test_plain_data():
    assert serialize_event({"msg": "hello"}) == '{"msg": "hello"}'
