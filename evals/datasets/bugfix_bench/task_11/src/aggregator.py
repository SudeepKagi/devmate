class Aggregator:
    _counts = {}

    def record(self, key):
        self._counts[key] = self._counts.get(key, 0) + 1

    def get_count(self, key):
        return self._counts.get(key, 0)

    def reset(self):
        # BUG: rebinds local variable instead of clearing class dict
        self._counts = {}
