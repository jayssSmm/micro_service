import asyncio
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import nats
import redis.asyncio as aioredis
from dotenv import load_dotenv

from app.extension import NATS_URL
from app.auth import auth

# ── Bootstrap 
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)



# otp.* matches otp.<email> — one token wildcard
NATS_SUBJECT    = "otp.*"

REDIS_HOST      = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT      = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB        = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD  = os.getenv("REDIS_PASSWORD", None)
OTP_TTL_SECONDS = 5 * 60  # 5 minutes

GMAIL_SENDER    = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASS  = os.getenv("GMAIL_APP_PASSWORD")  
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587  # STARTTLS


# ── Startup validation 
def _validate_env() -> None:
    missing = []
    if not GMAIL_SENDER:
        missing.append("GMAIL_SENDER")
    if not GMAIL_APP_PASS:
        missing.append("GMAIL_APP_PASSWORD")
    if missing:
        logger.critical("Missing required env vars: %s — set them in .env and restart.", missing)
        sys.exit(1)


# ── Redis helpers 
async def store_otp(rc: aioredis.Redis, email: str, otp: str) -> None:
    """
    Stores  key=<email>  value=<otp>  with a 5-minute TTL.
    e.g.  SET user@example.com 048271 EX 300
    """
    await rc.set(email, otp, ex=OTP_TTL_SECONDS)
    logger.info("Redis SET | key=%s | ttl=%ds", email, OTP_TTL_SECONDS)


async def delete_otp(rc: aioredis.Redis, email: str) -> None:
    """Best-effort cleanup — called before crashing on an email failure."""
    try:
        await rc.delete(email)
        logger.info("Redis DEL | key=%s", email)
    except Exception as exc:
        logger.error("Redis cleanup failed | key=%s | error=%s", email, exc)


# ── Gmail SMTP helper 
def send_otp_email(to_email: str, otp: str) -> None:
    """
    Sends an OTP email via Gmail SMTP using an app password.
    Uses STARTTLS on port 587. Raises on any failure.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your One-Time Password"
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = to_email

    plain = (
        f"Your OTP is: {otp}\n"
        f"It expires in 5 minutes.\n\n"
        f"If you did not request this, please ignore this email."
    )
    html = f"""\
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
        <h2>Your OTP Code</h2>
        <p>Use the code below to verify your identity.
           It expires in <strong>5 minutes</strong>.</p>
        <div style="font-size: 2rem; font-weight: bold; letter-spacing: 0.4rem;
                    background: #f4f4f4; padding: 16px; border-radius: 8px;
                    text-align: center;">
            {otp}
        </div>
        <p style="color: #888; font-size: 0.85rem; margin-top: 16px;">
            If you did not request this, please ignore this email.
        </p>
    </div>
    """

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_SENDER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_SENDER, to_email, msg.as_string())

    logger.info("Email sent via Gmail SMTP | to=%s", to_email)


async def handle_message(rc: aioredis.Redis, payload: dict) -> None:  # FIX: was nats.Msg
    logger.info("Message received")

    try:
        email  = payload["email"].strip().lower()
        otp    = payload.get("otp")
        action = payload.get("action", "send_otp")
    except KeyError as exc:
        logger.error("Malformed payload — skipping | error=%s", exc)
        return

    try:
        if action == "send_otp":
            send_otp_email(email, otp)
        elif action == "confirmed":
            auth.send_confirmation_email(email)
    except Exception as exc:
        logger.critical("Gmail SMTP failed | email=%s | error=%s", email, exc)
        sys.exit(1)


# ── Main 
async def main() -> None:
    _validate_env()

    # ── Redis 
    logger.info("Connecting to Redis | %s:%d db=%d", REDIS_HOST, REDIS_PORT, REDIS_DB)
    rc = aioredis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )
    try:
        await rc.ping()
        logger.info("Redis OK.")
    except Exception as exc:
        logger.critical("Cannot reach Redis: %s", exc)
        sys.exit(1)

    # ── NATS 
    logger.info("Connecting to NATS | %s", NATS_URL)
    try:
        nc = await nats.connect(NATS_URL)
        logger.info("NATS OK.")
    except Exception as exc:
        logger.critical("Cannot reach NATS: %s", exc)
        await rc.aclose()
        sys.exit(1)

    # ── Subscribe to otp.* 
    async def on_message(msg: nats.aio.client.Msg) -> None:
        await handle_message(rc, msg)

    await nc.subscribe(NATS_SUBJECT, cb=on_message)
    logger.info("Subscribed to '%s'. Waiting for messages...", NATS_SUBJECT)

    # ── Keep alive 
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down gracefully...")
    finally:
        await nc.drain()
        await rc.aclose()
        logger.info("Connections closed. Bye.")


if __name__ == "__main__":
    asyncio.run(main())