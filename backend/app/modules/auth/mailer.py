"""P10-B01: minimal outbound email for activation / reset links.

Uses stdlib smtplib (run in a worker thread) so no extra dependency is
needed. With SMTP_HOST unset nothing is sent and the caller learns that, so a
link is never written to logs - the bootstrap CLI prints it to the operator
instead, and local dev gets `debug_token` in the API response.
"""
import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def mail_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from)


def _send_blocking(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


async def send_email(*, to: str, subject: str, body: str) -> bool:
    """Returns True if handed to the SMTP server; never raises (a failed
    send must not reveal whether the account exists)."""
    if not mail_configured():
        logger.warning("Email not sent: SMTP is not configured.")
        return False
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        await asyncio.to_thread(_send_blocking, message)
    except Exception:  # noqa: BLE001 - delivery problems are operational, not user-facing
        logger.exception("Failed to send email.")
        return False
    return True
