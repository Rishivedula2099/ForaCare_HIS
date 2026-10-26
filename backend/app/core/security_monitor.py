"""P10-S02: abnormal-authentication detector.

Sliding-window counters over failed sign-ins and permission denials. When a
threshold is crossed it raises ONE `security_alert` per (type, subject) per
window: a structured ERROR log line (what a log-based alert rule matches), a
`his_security_alerts_total{type}` increment, and - if configured - a webhook
message. Thresholds come from settings (AUTH_ALERT_*).

Privacy: the attempted username is never recorded raw (people type passwords into
username boxes); alerts carry a short SHA-256 prefix, enough to correlate attempts
against one account, plus the client IP.
"""
import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from app.core import alerting, metrics
from app.core.config import get_settings
from app.core.logging import log_event

logger = logging.getLogger(__name__)

PERMISSION_DENIED_BURST = 10  # denials by one user inside the window


def pseudonym(username: str) -> str:
    return hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()[:10]


@dataclass(frozen=True)
class SecurityAlert:
    type: str
    subject: str
    count: int
    window_seconds: int


class AuthActivityMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_ip: dict[str, deque] = defaultdict(deque)  # (ts, user_hash)
        self._by_user: dict[str, deque] = defaultdict(deque)  # ts
        self._denied: dict[str, deque] = defaultdict(deque)  # ts
        self._alerted: dict[tuple[str, str], float] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_ip.clear()
            self._by_user.clear()
            self._denied.clear()
            self._alerted.clear()

    @staticmethod
    def _trim(queue: deque, cutoff: float, *, timestamped_pairs: bool = False) -> None:
        while queue and (queue[0][0] if timestamped_pairs else queue[0]) < cutoff:
            queue.popleft()

    def _should_alert(self, kind: str, subject: str, now: float, window: int) -> bool:
        last = self._alerted.get((kind, subject))
        if last is not None and now - last < window:
            return False
        self._alerted[(kind, subject)] = now
        if len(self._alerted) > 10_000:  # bound memory under an attack
            for key in [k for k, t in self._alerted.items() if now - t > window]:
                del self._alerted[key]
        return True

    def record_login_failure(self, ip: str | None, username: str) -> list[SecurityAlert]:
        settings = get_settings()
        window = settings.auth_alert_window_seconds
        now = time.monotonic()
        cutoff = now - window
        ip_key = ip or "unknown"
        user_key = pseudonym(username)
        raised: list[SecurityAlert] = []
        with self._lock:
            by_ip = self._by_ip[ip_key]
            by_ip.append((now, user_key))
            self._trim(by_ip, cutoff, timestamped_pairs=True)
            by_user = self._by_user[user_key]
            by_user.append(now)
            self._trim(by_user, cutoff)

            if len(by_ip) >= settings.auth_alert_failed_logins_per_ip and self._should_alert(
                "failed_logins_per_ip", ip_key, now, window
            ):
                raised.append(SecurityAlert("failed_logins_per_ip", ip_key, len(by_ip), window))
            distinct = len({u for _, u in by_ip})
            if distinct >= settings.auth_alert_distinct_users_per_ip and self._should_alert(
                "many_usernames_per_ip", ip_key, now, window
            ):
                raised.append(SecurityAlert("many_usernames_per_ip", ip_key, distinct, window))
            if len(by_user) >= settings.auth_alert_failed_logins_per_user and self._should_alert(
                "failed_logins_per_user", user_key, now, window
            ):
                raised.append(SecurityAlert("failed_logins_per_user", user_key, len(by_user), window))
            if len(self._by_ip) > 20_000:
                for key in [k for k, q in self._by_ip.items() if not q or q[-1][0] < cutoff]:
                    del self._by_ip[key]
        for alert in raised:
            self._emit(alert, ip=ip_key if alert.type != "failed_logins_per_user" else None,
                       user_hash=user_key if alert.type == "failed_logins_per_user" else None)
        return raised

    def record_permission_denied(self, user_id: str) -> list[SecurityAlert]:
        window = get_settings().auth_alert_window_seconds
        now = time.monotonic()
        raised: list[SecurityAlert] = []
        with self._lock:
            queue = self._denied[user_id]
            queue.append(now)
            self._trim(queue, now - window)
            if len(queue) >= PERMISSION_DENIED_BURST and self._should_alert("permission_denied_burst", user_id, now, window):
                raised.append(SecurityAlert("permission_denied_burst", user_id, len(queue), window))
        for alert in raised:
            self._emit(alert, user_id=user_id)
        return raised

    def refresh_token_reuse(self, user_id: str) -> SecurityAlert:
        """A replayed refresh token means a stolen one: always alert, once per user per window."""
        window = get_settings().auth_alert_window_seconds
        alert = SecurityAlert("refresh_token_reuse", user_id, 1, window)
        with self._lock:
            fresh = self._should_alert(alert.type, user_id, time.monotonic(), window)
        if fresh:
            self._emit(alert, user_id=user_id)
        return alert

    def _emit(self, alert: SecurityAlert, **facts) -> None:
        metrics.inc("his_security_alerts_total", {"type": alert.type})
        log_event(
            logger,
            logging.ERROR,
            "security_alert",
            alert_type=alert.type,
            count=alert.count,
            window_seconds=alert.window_seconds,
            **{k: v for k, v in facts.items() if v is not None},
        )
        alerting.notify(
            f"security:{alert.type}:{alert.subject}",
            f"Security alert: {alert.type.replace('_', ' ')}",
            count=alert.count,
            window_seconds=alert.window_seconds,
            **{k: v for k, v in facts.items() if v is not None},
        )


monitor = AuthActivityMonitor()
