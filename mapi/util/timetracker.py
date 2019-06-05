import time


class TimeTracker:
    __slots__ = ['start', 'end', 'elapsed']

    def __init__(self):
        self.start = None
        self.end = None
        self.elapsed = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.end = time.time()
        self.elapsed = (self.end - self.start)
