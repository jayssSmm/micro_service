import base64
import logging
from email.mime.text import MIMEText

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

from app import config

logger = logging.getLogger(__name__)

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _get_access_token() -> str:
    """
    Exchanges the long-lived refresh token for a short-lived access token.
    This is a sync network call under the hood, but it's fast (~100-300ms).
    """
    creds = Credentials(
        token=None,
        refresh_token=config.GMAIL_REFRESH_TOKEN,
        client_id=config.GMAIL_CLIENT_ID,
        client_secret=config.GMAIL_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(GoogleAuthRequest())
    return creds.token


def _build_raw_message(to_email: str, subject: str, body: str) -> str:
    msg = MIMEText(body, "plain")
    msg["From"] = config.GMAIL_SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Sends via Gmail API over HTTPS — works on Render free tier since
    no SMTP port is ever touched. Raises on failure, same as before,
    so send_email_with_retry's try/except still works unchanged.
    """
    access_token = _get_access_token()
    raw_message = _build_raw_message(to_email, subject, body)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GMAIL_SEND_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw_message},
            timeout=10.0,
        )
        response.raise_for_status()


async def send_email_with_retry(to_email: str, subject: str, body: str, retries: int = 1):
    """
    Unchanged from your original — sends via Gmail API now instead of SMTP.
    Never raises — always returns (success: bool, error: str | None).
    """
    import asyncio  # local import kept minimal; move to top if you prefer

    attempts = retries + 1
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            await send_email(to_email, subject, body)
            return True, None
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "Gmail API send to %s failed (attempt %s/%s): %s",
                to_email, attempt, attempts, exc,
            )
            if attempt < attempts:
                await asyncio.sleep(config.SMTP_RETRY_BACKOFF_SECONDS)
    return False, last_error