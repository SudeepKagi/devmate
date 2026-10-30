from src.aggregator import Aggregator
def test_hidden_new_instance():
    a1 = Aggregator()
    a1.reset()
    a1.record("k")
    a2 = Aggregator()
    a2.reset()
    assert a1.get_count("k") == 0
