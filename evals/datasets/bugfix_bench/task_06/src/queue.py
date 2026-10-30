class PriorityQueue:
    def __init__(self):
        self._items = []

    def push(self, item, priority):
        self._items.append((priority, item))
        # BUG: ascending order instead of descending
        self._items.sort(key=lambda x: x[0])

    def pop(self):
        if not self._items:
            return None
        return self._items.pop(0)[1]
