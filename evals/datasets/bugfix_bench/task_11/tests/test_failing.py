from src.aggregator import Aggregator
def test_reset():
    a = Aggregator()
    a.record("x")
    a.reset()
    assert a.get_count("x") == 0
