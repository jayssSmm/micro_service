import json
import random
import re
from datetime import datetime, timezone

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    """
    Maps an email to a NATS subject: otp.<email>
    e.g.  user@example.com  →  otp.user@example.com
    """
    return f"otp.{email}"


def build_payload(email: str, otp: str) -> bytes:
    """Serialises the NATS message payload to UTF-8 encoded JSON."""
    data = {
        "email": email,
        "otp": otp,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(data).encode("utf-8") 