import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.context import get_request_id


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class SecretRedactionFilter(logging.Filter):
    """Defense in depth (P8-B04): masks configured integration credentials if
    one ever ends up in a log message or its arguments. The adapters never
    log them; this catches a future mistake or a library echoing one."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        # Short values would redact ordinary text; real credentials are longer.
        self._secrets = [s for s in secrets if len(s) >= 6]

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secrets:
            message = record.getMessage()
            if any(secret in message for secret in self._secrets):
                for secret in self._secrets:
                    message = message.replace(secret, "[REDACTED]")
                record.msg, record.args = message, None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(
        SecretRedactionFilter(
            [
                settings.abdm_client_secret.get_secret_value(),
                settings.abdm_client_id,
                settings.jwt_access_secret_key,
                settings.jwt_refresh_secret_key,
                settings.qr_signing_secret_key,
            ]
        )
    )

    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | request_id=%(request_id)s | %(message)s"
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # httpx logs every request URL at INFO; our own `app.integrations.abdm`
    # line already records each call, without URLs or payloads.
    for http_logger in ("httpx", "httpcore"):
        logging.getLogger(http_logger).setLevel(logging.WARNING)

    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy_logger).handlers = [handler]
        logging.getLogger(noisy_logger).propagate = False
