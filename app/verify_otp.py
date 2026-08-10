"""
email_worker.py — NATS → SMTP confirmation mailer

Subscribes to the `email.success` subject published by verify_otp.py.
For every message it receives it sends a sign-in confirmation email to
the user via SMTP (works with Gmail, SendGrid SMTP relay, Mailtrap, etc.).

Run:
    python email_worker.py

Required env vars (add to .env):
    NATS_URL          nats://localhost:4222
    SMTP_HOST         smtp.gmail.com
    SMTP_PORT         587
    SMTP_USER         you@gmail.com
    SMTP_PASSWORD     your-app-password   (Gmail: create an App Password)
    EMAIL_FROM        You <you@gmail.com>  (display name + address)

Optional:
    SMTP_USE_TLS      true   (default true  — uses STARTTLS on port 587)
                             set false for SSL-on-connect (port 465)
"""

import asyncio
import json
import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import nats
from dotenv import load_dotenv

# ── Bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
NATS_URL      = os.getenv("NATS_URL")
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))

SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)

SMTP_USE_TLS  = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

NATS_SUBJECT  = "email.success"


# ── Email builder ─────────────────────────────────────────────────────────────
def build_confirmation_email(to_email: str, user_id: str, verified_at: str) -> MIMEMultipart:
    """
    Returns a MIMEMultipart message with both a plain-text and an HTML part.
    """
    # Parse ISO timestamp for a friendlier display
    try:
        dt = datetime.fromisoformat(verified_at)
        friendly_time = dt.strftime("%d %b %Y at %H:%M UTC")
    except ValueError:
        friendly_time = verified_at

    subject = "You're in — account verified ✅"

    plain = f"""\
Hi there,

Your account has been successfully verified and you are now signed in.

Account details
  Email      : {to_email}
  User ID    : {user_id}
  Verified at: {friendly_time}

If you didn't request this, please contact support immediately.

— The Team
"""

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Account Verified</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,.08);">

          <!-- Header -->
          <tr>
            <td style="background:#4f46e5;padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">
                Account Verified ✅
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;color:#374151;font-size:15px;line-height:1.6;">
              <p style="margin:0 0 16px;">Hi there,</p>
              <p style="margin:0 0 24px;">
                Your account has been <strong>successfully verified</strong> and
                you are now signed in. Welcome aboard!
              </p>

              <!-- Details box -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#f9fafb;border:1px solid #e5e7eb;
                            border-radius:6px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 8px;font-size:13px;color:#6b7280;
                               text-transform:uppercase;letter-spacing:.05em;">
                      Account details
                    </p>
                    <table cellpadding="4" cellspacing="0" style="font-size:14px;color:#111827;">
                      <tr>
                        <td style="color:#6b7280;padding-right:16px;">Email</td>
                        <td><strong>{to_email}</strong></td>
                      </tr>
                      <tr>
                        <td style="color:#6b7280;padding-right:16px;">User&nbsp;ID</td>
                        <td><code style="font-size:12px;">{user_id}</code></td>
                      </tr>
                      <tr>
                        <td style="color:#6b7280;padding-right:16px;">Verified&nbsp;at</td>
                        <td>{friendly_time}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="margin:0;font-size:13px;color:#6b7280;">
                If you didn't request this, please contact support immediately.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                        padding:20px 40px;text-align:center;
                        font-size:12px;color:#9ca3af;">
              © {datetime.utcnow().year} The Team. All rights reserved.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))
    return msg


# ── SMTP sender ───────────────────────────────────────────────────────────────
def send_email(msg: MIMEMultipart, to_email: str) -> None:
    """
    Sends *msg* synchronously via SMTP.
    Runs inside asyncio.to_thread() so it never blocks the event loop.
    Supports both STARTTLS (port 587, default) and SSL-on-connect (port 465).
    """
    context = ssl.create_default_context()

    if SMTP_USE_TLS:
        # STARTTLS — plain connect, then upgrade
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
    else:
        # SSL-on-connect — e.g. port 465
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())


# ── NATS message handler ──────────────────────────────────────────────────────
async def handle_email_success(raw_msg) -> None:
    """
    Called for every message on `email.success`.

    Expected JSON payload:
        { "user_id": "...", "email": "...", "verified_at": "..." }
    """
    try:
        payload = json.loads(raw_msg.data.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error("Bad message payload | error=%s | raw=%s", exc, raw_msg.data)
        return

    email       = payload.get("email", "")
    user_id     = payload.get("user_id", "")
    verified_at = payload.get("verified_at", "")

    if not email:
        logger.error("email.success message missing 'email' field | payload=%s", payload)
        return

    logger.info("Received email.success | email=%s user_id=%s", email, user_id)

    msg = build_confirmation_email(email, user_id, verified_at)

    try:
        await asyncio.to_thread(send_email, msg, email)
        logger.info("Confirmation email sent | email=%s", email)
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP auth failed — check SMTP_USER / SMTP_PASSWORD | email=%s", email)
    except smtplib.SMTPException as exc:
        logger.error("SMTP error | email=%s | error=%s", email, exc)
    except Exception as exc:
        logger.error("Unexpected error sending email | email=%s | error=%s", email, exc)


# ── Main loop ─────────────────────────────────────────────────────────────────
async def main() -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.critical(
            "SMTP_USER and SMTP_PASSWORD must be set in environment. Exiting."
        )
        return

    logger.info("Connecting to NATS at %s …", NATS_URL)
    nc = await nats.connect(NATS_URL)
    logger.info("NATS connected.")

    sub = await nc.subscribe(NATS_SUBJECT, cb=handle_email_success)
    logger.info("Subscribed to '%s'. Waiting for events …", NATS_SUBJECT)

    try:
        # Run forever until interrupted
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down …")
    finally:
        await sub.unsubscribe()
        await nc.drain()
        logger.info("NATS connection closed.")


if __name__ == "__main__":
    asyncio.run(main())