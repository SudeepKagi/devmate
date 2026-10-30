from src.aggregator import Aggregator
def test_record():
    a = Aggregator()
    a.record("a")
    assert a.get_count("a") >= 1
