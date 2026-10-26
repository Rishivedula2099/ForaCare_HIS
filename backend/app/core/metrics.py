"""P10-S02: a small, dependency-free metrics registry rendered in the Prometheus
text format (GET /internal/metrics).

Labels are only ever drawn from closed sets (HTTP method, matched route
TEMPLATE, status class, event names) - never from user input, identifiers or
patient data - so cardinality stays bounded and nothing sensitive can leak
through a label. State is per process; the API runs one worker.
"""
import threading
from collections import defaultdict

_lock = threading.Lock()

_COUNTERS: dict[str, dict[tuple, float]] = defaultdict(dict)
_HISTOGRAMS: dict[str, dict[tuple, list[float]]] = defaultdict(dict)
_GAUGES: dict[str, dict[tuple, float]] = defaultdict(dict)

DURATION_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

HELP = {
    "his_http_requests_total": ("counter", "HTTP requests by method, route template and status class."),
    "his_http_request_duration_seconds": ("histogram", "HTTP request latency by route template."),
    "his_unhandled_exceptions_total": ("counter", "Requests that ended in an unhandled exception (HTTP 500)."),
    "his_server_errors_total": ("counter", "Handled errors that mapped to HTTP 5xx, by error code."),
    "his_auth_events_total": ("counter", "Authentication and authorisation events by type."),
    "his_security_alerts_total": ("counter", "Security alerts raised by the abnormal-activity detector."),
    "his_rate_limited_total": ("counter", "Requests rejected by a rate limit, by limiter scope."),
    "his_ready": ("gauge", "1 when a readiness check passes, 0 when it fails."),
    "his_app_info": ("gauge", "Build information (value is always 1)."),
}

#: Audit actions worth counting (kept small and fixed).
AUTH_EVENT_BY_AUDIT_ACTION = {
    "auth.login.succeeded": "login_succeeded",
    "auth.login.failed": "login_failed",
    "auth.logout": "logout",
    "auth.security.refresh_reuse_detected": "refresh_token_reuse",
    "auth.password_reset_requested": "password_reset_requested",
    "auth.password_reset_completed": "password_reset_completed",
    "auth.otp.verification_failed": "otp_failed",
    "security.permission_denied": "permission_denied",
    "security.abnormal_auth_activity": "abnormal_auth_activity",
}


def _key(labels: dict | None) -> tuple:
    return tuple(sorted((labels or {}).items()))


def inc(name: str, labels: dict | None = None, value: float = 1.0) -> None:
    with _lock:
        series = _COUNTERS[name]
        series[_key(labels)] = series.get(_key(labels), 0.0) + value


def observe(name: str, value: float, labels: dict | None = None) -> None:
    with _lock:
        series = _HISTOGRAMS[name]
        key = _key(labels)
        # [bucket counts..., +Inf count, sum]
        data = series.setdefault(key, [0.0] * (len(DURATION_BUCKETS) + 2))
        for i, bound in enumerate(DURATION_BUCKETS):
            if value <= bound:
                data[i] += 1
        data[len(DURATION_BUCKETS)] += 1
        data[-1] += value


def set_gauge(name: str, value: float, labels: dict | None = None) -> None:
    with _lock:
        _GAUGES[name][_key(labels)] = value


def count_audit_action(action: str) -> None:
    event = AUTH_EVENT_BY_AUDIT_ACTION.get(action)
    if event:
        inc("his_auth_events_total", {"event": event})


def status_class(status: int) -> str:
    return f"{status // 100}xx"


def reset() -> None:
    """Test helper."""
    with _lock:
        _COUNTERS.clear()
        _HISTOGRAMS.clear()
        _GAUGES.clear()


def counter_value(name: str, labels: dict | None = None) -> float:
    with _lock:
        return _COUNTERS.get(name, {}).get(_key(labels), 0.0)


def counter_total(name: str) -> float:
    with _lock:
        return sum(_COUNTERS.get(name, {}).values())


def _fmt_labels(key: tuple, extra: tuple = ()) -> str:
    pairs = list(key) + list(extra)
    if not pairs:
        return ""
    body = ",".join(f'{k}="{str(v).replace(chr(92), "").replace(chr(34), "")}"' for k, v in pairs)
    return "{" + body + "}"


def render() -> str:
    lines: list[str] = []
    with _lock:
        names = sorted(set(_COUNTERS) | set(_HISTOGRAMS) | set(_GAUGES))
        for name in names:
            kind, text = HELP.get(name, ("untyped", name))
            lines.append(f"# HELP {name} {text}")
            lines.append(f"# TYPE {name} {kind}")
            for key, value in sorted(_COUNTERS.get(name, {}).items()):
                lines.append(f"{name}{_fmt_labels(key)} {value:g}")
            for key, value in sorted(_GAUGES.get(name, {}).items()):
                lines.append(f"{name}{_fmt_labels(key)} {value:g}")
            for key, data in sorted(_HISTOGRAMS.get(name, {}).items()):
                for i, bound in enumerate(DURATION_BUCKETS):
                    lines.append(f"{name}_bucket{_fmt_labels(key, (('le', bound),))} {data[i]:g}")
                lines.append(f"{name}_bucket{_fmt_labels(key, (('le', '+Inf'),))} {data[len(DURATION_BUCKETS)]:g}")
                lines.append(f"{name}_sum{_fmt_labels(key)} {data[-1]:.6f}")
                lines.append(f"{name}_count{_fmt_labels(key)} {data[len(DURATION_BUCKETS)]:g}")
    return "\n".join(lines) + "\n"
