import time
from collections import deque, defaultdict


class RateLimitService:
    def __init__(self):
        self._windows = defaultdict(deque)

    def allow(self, key, limit, window_seconds):
        now = time.time()
        bucket = self._windows[key]

        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            return False

        bucket.append(now)
        return True


rate_limit_service = RateLimitService()
