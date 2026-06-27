import time
from collections import deque, defaultdict


class RateLimitService:
    def __init__(self):
        self._windows = defaultdict(deque)
        self._markers = {}

    def _prune_bucket(self, bucket, now, window_seconds):
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _prune_markers(self, now):
        expired_keys = [key for key, expires_at in self._markers.items() if expires_at <= now]
        for key in expired_keys:
            self._markers.pop(key, None)

    def allow(self, key, limit, window_seconds):
        return self.consume([(key, limit, window_seconds)])["allowed"]

    def consume(self, checks):
        now = time.time()
        prepared = []

        for key, limit, window_seconds in checks:
            normalized_limit = max(1, int(limit))
            normalized_window = max(1, int(window_seconds))
            bucket = self._windows[key]
            self._prune_bucket(bucket, now, normalized_window)

            if len(bucket) >= normalized_limit:
                retry_after = max(1, int(bucket[0] + normalized_window - now))
                return {
                    "allowed": False,
                    "key": key,
                    "limit": normalized_limit,
                    "windowSeconds": normalized_window,
                    "remaining": 0,
                    "retryAfterSeconds": retry_after,
                }

            prepared.append((bucket, normalized_limit, normalized_window, key))

        for bucket, _limit, _window_seconds, _key in prepared:
            bucket.append(now)

        if not prepared:
            return {"allowed": True, "remaining": None, "retryAfterSeconds": 0}

        tightest_remaining = min(limit - len(bucket) for bucket, limit, _window_seconds, _key in prepared)
        return {
            "allowed": True,
            "remaining": max(0, tightest_remaining),
            "retryAfterSeconds": 0,
        }

    def mark_once(self, key, ttl_seconds):
        now = time.time()
        self._prune_markers(now)

        if key in self._markers and self._markers[key] > now:
            return False

        self._markers[key] = now + max(1, int(ttl_seconds))
        return True


rate_limit_service = RateLimitService()
