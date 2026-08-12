import hmac
import logging

from fastapi import APIRouter, HTTPException

from app import extension, config
from app.auth import auth
from app.models import otp_models
from app import otp_store
from app.email.email_utils import send_email_with_retry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/verify-otp", response_model=otp_models.VerifyOTPResponse)
async def verify_otp(request: otp_models.VerifyOTPRequest):
    raw_email = request.email.strip().lower()
    submitted_otp = request.otp.strip()

    try:
        record = await otp_store.get_otp_record(raw_email)
    except Exception:
        logger.exception("Redis unavailable while verifying OTP for %s", raw_email)
        raise HTTPException(status_code=503, detail="Could not verify right now. Please try again.")

    if record is None:
        raise HTTPException(status_code=400, detail="Code expired or not found. Please request a new one.")

    if record.get("attempts", 0) >= config.MAX_OTP_ATTEMPTS:
        try:
            await otp_store.delete_otp(raw_email)
        except Exception:
            logger.exception("Failed to clear locked-out OTP for %s", raw_email)
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new code.")

    if not hmac.compare_digest(str(record.get("otp", "")), submitted_otp):
        try:
            attempts = await otp_store.increment_attempts(raw_email, record)
        except Exception:
            logger.exception("Failed to record attempt for %s", raw_email)
            attempts = record.get("attempts", 0) + 1
        remaining = max(config.MAX_OTP_ATTEMPTS - attempts, 0)
        raise HTTPException(status_code=422, detail=f"Invalid code. {remaining} attempt(s) remaining.")

    try:
        await otp_store.delete_otp(raw_email)
    except Exception:
        logger.exception("Failed to delete used OTP for %s", raw_email)

    await _notify_signed_in(raw_email)

    return otp_models.VerifyOTPResponse(message="Verified successfully.", email=raw_email)


async def _notify_signed_in(email: str) -> None:
    if extension.nats_available():
        try:
            subject = auth.build_nats_subject(email, config.CONFIRM_SUBJECT_PREFIX)
            payload = auth.build_payload(email)
            await extension.nc.publish(subject, payload)
            return
        except Exception:
            logger.exception(
                "Failed to publish sign-in confirmation for %s — falling back to direct SMTP.", email,
            )

    success, error = await send_email_with_retry(
        email, "You're signed in", "You have successfully signed in.", retries=1,
    )
    if not success:
        logger.error("Could not send sign-in confirmation to %s: %s", email, error)