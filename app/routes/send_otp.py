import json
import logging

from fastapi import APIRouter, HTTPException

from app import extension, config
from app.auth import auth
from app.models import otp_models
from app import otp_store
from app.email.email_utils import send_email_with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/send-otp", response_model=otp_models.OTPResponse)
async def send_otp(request: otp_models.OTPRequest):
    raw_email = request.email.strip().lower()

    is_valid, error_msg = auth.validate_email(raw_email)
    if not is_valid:
        logger.warning("Invalid email received: %r — %s", raw_email, error_msg)
        raise HTTPException(status_code=422, detail=error_msg)

    otp = auth.generate_otp()

    try:
        await otp_store.store_otp(raw_email, otp, config.OTP_TTL_SECONDS)
    except Exception:
        logger.exception("Redis unavailable — could not store OTP for %s", raw_email)
        raise HTTPException(
            status_code=503,
            detail="Could not start sign-in right now. Please try again shortly.",
        )

    sent, error = await _deliver_otp(raw_email, otp)

    if not sent:
        logger.error("Failed to deliver OTP to %s: %s", raw_email, error)
        raise HTTPException(
            status_code=503,
            detail="We couldn't send the code to that address. Please try again.",
        )

    logger.info("OTP delivered to %s", raw_email)
    return otp_models.OTPResponse(message="OTP sent successfully.", email=raw_email)


async def _deliver_otp(email: str, otp: str):
    if extension.nats_available():
        subject = auth.build_nats_subject(email, config.SEND_OTP_SUBJECT_PREFIX)
        payload = auth.build_payload(email, otp)
        try:
            reply = await extension.nc.request(subject, payload, timeout=config.NATS_OTP_REQUEST_TIMEOUT)
            data = json.loads(reply.data.decode())
            return bool(data.get("success")), data.get("error")
        except Exception as exc:
            logger.warning(
                "NATS delivery request failed for %s (%s) — falling back to direct SMTP.",
                email, exc,
            )
            # fall through to the direct-SMTP path below

    return await send_email_with_retry(
        email,
        "Your sign-in code",
        f"Your one-time code is {otp}. It expires in 5 minutes.",
        retries=1,
    )