import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
NATS_URL = os.getenv("NATS_URL")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))  # 5 minutes
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "5"))

# How long /auth/send-otp will block waiting for the NATS worker to
# confirm the email actually went out (must comfortably cover one
# SMTP attempt + one retry + backoff).
NATS_OTP_REQUEST_TIMEOUT = float(os.getenv("NATS_OTP_REQUEST_TIMEOUT", "20"))
SMTP_RETRY_BACKOFF_SECONDS = float(os.getenv("SMTP_RETRY_BACKOFF_SECONDS", "2"))

SEND_OTP_SUBJECT_PREFIX = "otp.send"
CONFIRM_SUBJECT_PREFIX = "otp.confirm"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")