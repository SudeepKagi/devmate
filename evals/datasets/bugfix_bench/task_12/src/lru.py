class LRUCache:
    def __init__(self, capacity=2):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        if key not in self.cache:
            return None
        # BUG: missing self.order.remove(key); self.order.append(key)
        return self.cache[key]

    def put(self, key, val):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = val
        self.order.append(key)
