import json
import random
import re
from datetime import datetime, timezone
from app.extension import nc
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

logger = logging.getLogger(__name__)

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")  # FIX: was missing
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))           # FIX: was missing
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")             # FIX: GMAIL_APP_PASS → SMTP_PASSWORD
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)

NATS_SUBJECT = "otp.*"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

async def handle_otp(payload: dict) -> tuple[bool, str]:
    email = payload.get("email", "")
    
    is_valid, error = validate_email(email)
    if not is_valid:
        return False, error

    email = email.strip().lower()
    otp   = generate_otp()

    subject = build_nats_subject(email)
    data    = build_payload(email, otp)

    await nc.publish(subject, data)
    return True, "OTP sent."


def validate_email(email: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Runs a series of basic checks before the regex so the error is specific.
    """
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
    """Returns a zero-padded 6-digit OTP string."""
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def build_nats_subject(email: str) -> str:
    safe = email.replace("@", "_at_").replace(".", "_")  # FIX: otp.user@example.com is invalid
    return f"otp.{safe}"


def build_payload(email: str, otp: str) -> bytes:
    """Serialises the NATS message payload to UTF-8 encoded JSON."""
    data = {
        "email": email,
        "otp": otp,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(data).encode("utf-8") 

def send_confirmation_email(to_email: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Identity Verified"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    plain = "Your identity has been successfully verified."
    html  = """\
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
        <h2>✅ Verified</h2>
        <p>Your identity has been successfully verified.</p>
    </div>
    """
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)          # FIX: was EMAIL_FROM, GMAIL_APP_PASS
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())

    logger.info("Confirmation email sent | to=%s", to_email)