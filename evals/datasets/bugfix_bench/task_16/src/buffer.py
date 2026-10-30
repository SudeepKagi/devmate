class CircularBuffer:
    def __init__(self, size=3):
        self.size = size
        self.data = [None] * size
        self.write_idx = 0
        self.count = 0

    def append(self, val):
        self.data[self.write_idx] = val
        self.write_idx = (self.write_idx + 1) % self.size
        if self.count < self.size:
            self.count += 1

    def get_all(self):
        # BUG: doesn't handle read order when wrapped
        if self.count < self.size:
            return self.data[:self.count]
        # When full, oldest item is at write_idx
        res = []
        for i in range(self.size):
            idx = (self.write_idx + i) % self.size
            res.append(self.data[idx])
        return res
