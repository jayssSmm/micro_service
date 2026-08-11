import asyncio
import json
import logging
import os
import random
import re
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import app.extension as extension
from app.worker import start_worker

logger = logging.getLogger(__name__)

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", 300))

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── NATS worker entry point ──────────────────────────────
async def start_otp_worker():
    await start_worker("otp.*", _handle_nats_message)


async def _handle_nats_message(payload: dict) -> None:
    """Called by start_worker for every message on otp.*"""
    email  = payload.get("email", "").strip().lower()
    otp    = payload.get("otp")
    action = payload.get("action", "send_otp")

    if not email:
        logger.error("Missing email in payload: %s", payload)
        return

    if action == "send_otp":
        # write Redis
        try:
            await extension.rc.set(email, otp, ex=OTP_TTL_SECONDS)
            logger.info("Redis SET | key=%s", email)
        except Exception as exc:
            logger.critical("Redis write failed | %s", exc)
            return

        # send email
        try:
            await asyncio.to_thread(send_otp_email, email, otp)
        except Exception as exc:
            logger.critical("SMTP failed | %s", exc)
            await extension.rc.delete(email)

    elif action == "confirmed":
        try:
            await asyncio.to_thread(send_confirmation_email, email)
        except Exception as exc:
            logger.error("Confirmation email failed | %s", exc)


# ── Backend helper (called by send_otp route) ───────────
def validate_email(email: str) -> tuple[bool, str]:
    email = email.strip()
    if not email:
        return False, "Email must not be empty."
    if "@" not in email:
        return False, "Email must contain '@'."
    local, _, domain = email.partition("@")
    if not local:
        return False, "Email must have characters before '@'."
    if not domain:
        return False, "Email must have a domain after '@'."
    if "." not in domain:
        return False, "Email domain must contain at least one '.'."
    if not EMAIL_REGEX.match(email):
        return False, "Email format is invalid."
    return True, ""


def generate_otp() -> str:
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def build_nats_subject(email: str) -> str:
    safe = email.replace("@", "_at_").replace(".", "_")
    return f"otp.{safe}"


def build_payload(email: str, otp: str) -> bytes:
    data = {
        "email": email,
        "otp": otp,
        "action": "send_otp",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(data).encode("utf-8")


# ── SMTP senders ─────────────────────────────────────────
def send_otp_email(to_email: str, otp: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your one-time code"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    plain = f"Your OTP is: {otp}\nIt expires in 5 minutes."
    html  = f"""\
    <div style="font-family:sans-serif;max-width:480px;margin:auto;">
        <h2>Your OTP code</h2>
        <div style="font-size:2rem;font-weight:bold;letter-spacing:0.4rem;
                    background:#f4f4f4;padding:16px;border-radius:8px;text-align:center;">
            {otp}
        </div>
        <p style="color:#888;font-size:0.85rem;margin-top:16px;">
            Expires in 5 minutes. If you didn't request this, ignore this email.
        </p>
    </div>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())

    logger.info("OTP email sent | to=%s", to_email)


def send_confirmation_email(to_email: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Identity verified"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    plain = "Your identity has been successfully verified."
    html  = """\
    <div style="font-family:sans-serif;max-width:480px;margin:auto;">
        <h2>✅ Verified</h2>
        <p>Your identity has been successfully verified.</p>
    </div>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())

    logger.info("Confirmation email sent | to=%s", to_email)