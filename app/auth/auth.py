import re
import secrets
import time
import json
import hashlib

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str):
    """Rudimentary format check — not a mailbox-existence check."""
    if not email:
        return False, "Email is required."
    if len(email) > 254:
        return False, "Email is too long."
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email address."
    return True, None


def generate_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _subject_safe_email(email: str) -> str:
    # NATS uses '.' as a subject hierarchy separator and email addresses
    # are full of them, so hash the email into an opaque token rather than
    # putting it in the subject verbatim — avoids accidental wildcard
    # collisions and keeps subjects flat.
    return hashlib.sha256(email.encode()).hexdigest()


def build_nats_subject(email: str, prefix: str) -> str:
    return f"{prefix}.{_subject_safe_email(email)}"


def build_payload(email: str, otp: str = "") -> bytes:
    return json.dumps({
        "email": email,
        "otp": otp,
        "timestamp": time.time(),
    }).encode()