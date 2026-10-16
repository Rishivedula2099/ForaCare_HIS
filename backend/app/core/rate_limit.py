"""P9-B01: in-process sliding-window rate limiting.

nginx rate-limits per IP in front of the app, but the API must also protect
itself when reached directly (dev, internal callers, a misrouted proxy rule).
State is per-process; behind several workers the effective limit is
`limit x workers`, which still bounds brute force. Swap `_hits` for Redis
if a shared budget is ever needed.
"""
import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core import metrics
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
_MAX_KEYS = 50_000


def client_ip(request: Request) -> str:
    # request.client reflects the real peer; X-Forwarded-For is spoofable
    # unless uvicorn is told which proxies to trust (--forwarded-allow-ips).
    return request.client.host if request.client else "unknown"


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """Records a hit for `key`; raises 429 once `limit` hits land in the window."""
    if not get_settings().rate_limit_enabled:
        return
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        if len(_hits) > _MAX_KEYS:
            for stale in [k for k, q in _hits.items() if not q or q[-1] < cutoff]:
                del _hits[stale]
        bucket = _hits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            metrics.inc("his_rate_limited_total", {"scope": key.split(":")[0]})
            logger.warning("security.rate_limited key=%s limit=%s/%ss", key.split(":")[0], limit, window_seconds)
            retry_after = max(1, int(bucket[0] + window_seconds - now) + 1)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


def rate_limit(scope: str, *, limit: int, window_seconds: int = 60):
    """FastAPI dependency limiting a route per client IP."""

    async def _dependency(request: Request) -> None:
        check_rate_limit(f"{scope}:{client_ip(request)}", limit=limit, window_seconds=window_seconds)

    return _dependency
