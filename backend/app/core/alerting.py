"""P10-S02: outbound alerts to an incoming webhook (Slack / Teams / Mattermost
style `{"text": "..."}`), for the few events someone must act on promptly:
security alerts and unhandled-error bursts.

* Off unless ALERT_WEBHOOK_URL is set; the URL is a secret (it embeds a token).
* Payloads carry only an event name, short summary, environment, request id and
  scalar facts such as counts and a pseudonymous username hash - never request
  bodies, credentials or patient data - and are scrubbed like every log line.
* Rate-limited per alert key (ALERT_COOLDOWN_SECONDS) so a storm cannot flood the
  channel; a failed delivery is logged and never raises into the request.
"""
import asyncio
import logging
import time

import httpx

from app.core.config import get_settings
from app.core.context import get_request_id
from app.core.logging import log_event, scrub

logger = logging.getLogger(__name__)

_last_sent: dict[str, float] = {}


def reset() -> None:
    _last_sent.clear()


def _cooled_down(key: str) -> bool:
    now = time.monotonic()
    cooldown = get_settings().alert_cooldown_seconds
    last = _last_sent.get(key)
    if last is not None and now - last < cooldown:
        return False
    _last_sent[key] = now
    return True


async def send_alert(key: str, summary: str, **facts) -> bool:
    """Returns True if an alert was handed to the webhook."""
    settings = get_settings()
    url = settings.alert_webhook_url.get_secret_value()
    if not url or not _cooled_down(key):
        return False
    detail = " ".join(f"{k}={scrub(str(v))}" for k, v in facts.items() if v is not None)
    request_id = get_request_id()
    text = f"[{settings.environment}] {scrub(summary)}"
    if detail:
        text += f" ({detail})"
    if request_id:
        text += f" request_id={request_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json={"text": text})
        if response.status_code >= 300:
            log_event(logger, logging.WARNING, "alert_delivery_failed", status=response.status_code, alert_key=key)
            return False
    except Exception as exc:  # noqa: BLE001 - alerting must never break the request
        log_event(logger, logging.WARNING, "alert_delivery_failed", error_type=type(exc).__name__, alert_key=key)
        return False
    return True


def notify(key: str, summary: str, **facts) -> None:
    """Fire-and-forget from sync or async code. Does nothing without a running loop."""
    if not get_settings().alert_webhook_url.get_secret_value():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(send_alert(key, summary, **facts))
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
