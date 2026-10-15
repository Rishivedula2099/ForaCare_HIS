import json
import logging
import re
import sys
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.context import get_request_id


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


REDACTED = "[REDACTED]"

# P9-B04: patterns that must never reach a log line, whatever put them there
# (our code, a library's exception text, a framework access log).
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")
_BEARER = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}")
_TOKEN_COOKIE = re.compile(r"(?i)\b((?:access|refresh)_token)=[^;\s,&\"']+")
_URL_CREDENTIALS = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^\s:/@]+):[^\s@/]+@")
_KEY_VALUE = re.compile(
    r"(?i)([\"']?\b(?:password|passwd|new_password|current_password|otp|code|client_secret|"
    r"secret|api[_-]?key|authorization)[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&)}\]]+)"
)
# SQLAlchemy appends the statement and every bound value to its error text -
# i.e. patient names, DOBs, password hashes and OTP hashes.
_SQL_DETAIL = re.compile(r"\[(?:SQL|parameters): .*?\](?=\s*(?:\(Background|$))", re.S)
_SQL_DETAIL_LOOSE = re.compile(r"\[parameters: .*", re.S)
_QUERY_STRING = re.compile(r"\?[^\s\"']*")


def scrub(text: str) -> str:
    """Masks credentials, tokens and bound SQL values in free text."""
    text = _SQL_DETAIL.sub("[SQL details removed]", text)
    text = _SQL_DETAIL_LOOSE.sub("[SQL details removed]", text)
    text = _JWT.sub(REDACTED, text)
    text = _BEARER.sub(r"\1 " + REDACTED, text)
    text = _TOKEN_COOKIE.sub(r"\1=" + REDACTED, text)
    text = _URL_CREDENTIALS.sub(r"\1:" + REDACTED + "@", text)
    return _KEY_VALUE.sub(lambda m: m.group(1) + REDACTED, text)


class SecretRedactionFilter(logging.Filter):
    """Defense in depth (P8-B04, widened in P9-B04): masks configured
    credentials and credential-shaped text (JWTs, bearer headers, token
    cookies, URL passwords, password/otp key-values, SQL bound parameters)
    in a record's message AND its exception text, and strips query strings
    from the server access log (patient searches and QR signatures travel
    in them)."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        # Short values would redact ordinary text; real credentials are longer.
        self._secrets = [s for s in secrets if len(s) >= 6]

    def _mask_secrets(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "uvicorn.access":
            # args = (client, method, path_with_query, http_version, status)
            if isinstance(record.args, tuple) and len(record.args) >= 3:
                args = list(record.args)
                args[2] = _QUERY_STRING.sub("", str(args[2]))
                record.args = tuple(args)

        message = record.getMessage()
        cleaned = scrub(self._mask_secrets(message))
        if cleaned != message:
            record.msg, record.args = cleaned, None

        if record.exc_info:
            # Render and scrub the traceback once; formatters reuse exc_text.
            rendered = logging.Formatter().formatException(record.exc_info)
            record.exc_text = scrub(self._mask_secrets(rendered))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = scrub(self._mask_secrets(record.exc_text))
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
        if record.exc_text:
            payload["exception"] = record.exc_text
        elif record.exc_info:
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
                settings.smtp_password.get_secret_value(),
                settings.jwt_access_secret_key,
                settings.jwt_refresh_secret_key,
                settings.qr_signing_secret_key,
                settings.database_password,
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
