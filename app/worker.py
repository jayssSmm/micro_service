import json
import logging

from app import extension, config
from app.email.email_utils import send_email_with_retry

logger = logging.getLogger(__name__)

_send_sub = None
_confirm_sub = None


async def _handle_send_otp(msg):
    try:
        payload = json.loads(msg.data.decode())
        email = payload["email"]
        otp = payload["otp"]
    except Exception:
        logger.exception("Malformed otp.send message: %r", msg.data[:200])
        await _safe_respond(msg, {"success": False, "error": "bad_payload"})
        return

    subject = "Your sign-in code"
    body = f"Your one-time code is {otp}. It expires in 5 minutes."

    success, error = await send_email_with_retry(email, subject, body, retries=1)
    await _safe_respond(msg, {"success": success, "error": error})


async def _handle_confirm_email(msg):
    try:
        payload = json.loads(msg.data.decode())
        email = payload["email"]
    except Exception:
        logger.exception("Malformed otp.confirm message: %r", msg.data[:200])
        return

    success, error = await send_email_with_retry(
        email,
        "You're signed in",
        "You have successfully signed in. If this wasn't you, please secure your account.",
        retries=1,
    )
    if not success:
        logger.error("Could not send sign-in confirmation to %s: %s", email, error)


async def _safe_respond(msg, data: dict) -> None:
    try:
        await msg.respond(json.dumps(data).encode())
    except Exception:
        logger.exception("Failed to respond to NATS message on subject=%s", msg.subject)


async def start_workers() -> None:
    global _send_sub, _confirm_sub
    if not extension.nats_available():
        logger.warning("NATS not connected — workers not started; endpoints will use direct SMTP.")
        return
    try:
        _send_sub = await extension.nc.subscribe(f"{config.SEND_OTP_SUBJECT_PREFIX}.*", cb=_handle_send_otp)
        _confirm_sub = await extension.nc.subscribe(f"{config.CONFIRM_SUBJECT_PREFIX}.*", cb=_handle_confirm_email)
        logger.info("NATS workers subscribed.")
    except Exception:
        logger.exception("Failed to start NATS workers — endpoints will use direct SMTP.")


async def stop_workers() -> None:
    global _send_sub, _confirm_sub
    for sub in (_send_sub, _confirm_sub):
        if sub:
            try:
                await sub.unsubscribe()
            except Exception:
                logger.exception("Error unsubscribing NATS worker")
    _send_sub = None
    _confirm_sub = None