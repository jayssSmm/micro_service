import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
NATS_URL = os.getenv("NATS_URL")

GMAIL_CLIENT_ID     = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN')
GMAIL_SENDER_EMAIL  = os.getenv('GMAIL_SENDER_EMAIL')

OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))  # 5 minutes
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "5"))


NATS_OTP_REQUEST_TIMEOUT = float(os.getenv("NATS_OTP_REQUEST_TIMEOUT", "20"))
SMTP_RETRY_BACKOFF_SECONDS = float(os.getenv("SMTP_RETRY_BACKOFF_SECONDS", "2"))

SEND_OTP_SUBJECT_PREFIX = "otp.send"
CONFIRM_SUBJECT_PREFIX = "otp.confirm"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")