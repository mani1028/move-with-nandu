from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException


_BUCKETS: dict[str, deque[datetime]] = {}
_LOCK = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enforce_rate_limit(key: str, limit: int, window_seconds: int, message: str) -> None:
    cutoff = _now() - timedelta(seconds=window_seconds)
    with _LOCK:
        bucket = _BUCKETS.get(key)
        if bucket is None:
            bucket = deque()
            _BUCKETS[key] = bucket

        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail=message)

        bucket.append(_now())


def get_client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def parse_version(version: str) -> tuple[int, int, int]:
    cleaned = (version or "").strip().lstrip("vV")
    parts = cleaned.split(".")
    nums: list[int] = []
    for i in range(3):
        if i < len(parts):
            part = parts[i]
            digits = "".join(ch for ch in part if ch.isdigit())
            nums.append(int(digits or "0"))
        else:
            nums.append(0)
    return (nums[0], nums[1], nums[2])


def is_version_below(current: str, minimum: str) -> bool:
    return parse_version(current) < parse_version(minimum)
