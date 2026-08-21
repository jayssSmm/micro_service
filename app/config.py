import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
NATS_URL = os.getenv("NATS_URL")

# Write the .creds content from env to a temp file for the NATS client
_raw_creds = os.getenv("NATS_CREDS", "")
if _raw_creds:
    if "\\n" in _raw_creds and "\n" not in _raw_creds:
        _raw_creds = _raw_creds.replace("\\n", "\n")
    _f = tempfile.NamedTemporaryFile(mode="w", suffix=".creds", delete=False)
    _f.write(_raw_creds)
    _f.close()
    NATS_CREDS_PATH = _f.name
else:
    NATS_CREDS_PATH = None

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "5"))

NATS_OTP_REQUEST_TIMEOUT = float(os.getenv("NATS_OTP_REQUEST_TIMEOUT", "20"))
SMTP_RETRY_BACKOFF_SECONDS = float(os.getenv("SMTP_RETRY_BACKOFF_SECONDS", "2"))

SEND_OTP_SUBJECT_PREFIX = "otp.send"
CONFIRM_SUBJECT_PREFIX = "otp.confirm"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")