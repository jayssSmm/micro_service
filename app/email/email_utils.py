import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app import config

logger = logging.getLogger(__name__)


def _send_sync(to_email: str, subject: str, body: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = config.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USER, [to_email], msg.as_string())


async def send_email(to_email: str, subject: str, body: str) -> None:
    # smtplib is blocking — push it to a thread so it never stalls the
    # asyncio event loop (and therefore the whole app).
    await asyncio.to_thread(_send_sync, to_email, subject, body)


async def send_email_with_retry(to_email: str, subject: str, body: str, retries: int = 1):
    """
    Sends an email, retrying `retries` more time(s) on failure.
    Never raises — always returns (success: bool, error: str | None).
    """
    attempts = retries + 1
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            await send_email(to_email, subject, body)
            return True, None
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "SMTP send to %s failed (attempt %s/%s): %s",
                to_email, attempt, attempts, exc,
            )
            if attempt < attempts:
                await asyncio.sleep(config.SMTP_RETRY_BACKOFF_SECONDS)
    return False, last_error