import os
from dotenv import load_dotenv

load_dotenv()

# ── NATS
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# ── Redis
REDIS_HOST     = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT     = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB       = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# ── SMTP
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)
SMTP_USE_TLS  = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

# ── App
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8000))

# ── CORS (comma-separated origins in .env)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ── OTP
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", 300))  # 5 minutes

# ── NATS subjects
NATS_SUBJECT_OTP      = "otp.*"
NATS_SUBJECT_CONFIRM  = "email.success"


def validate() -> None:
    """Call once at startup — crashes fast if required vars are missing."""
    required = {
        "SMTP_USER":     SMTP_USER,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "NATS_URL":      NATS_URL,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing} — set them in .env")