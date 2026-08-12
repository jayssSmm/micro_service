import app.extension as extension
from fastapi import APIRouter, HTTPException
from app.models import otp_models
from app.auth import auth
import os

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()
NATS_URL = os.getenv("NATS_URL")

@router.post("/auth/send-otp", response_model=otp_models.OTPResponse)
async def send_otp(request: otp_models.OTPRequest):
    raw_email = request.email.strip().lower()

    # ── Step 1: Validate 
    is_valid, error_msg = auth.validate_email(raw_email)
    if not is_valid:
        logger.warning("Invalid email received: %r — %s", raw_email, error_msg)
        raise HTTPException(status_code=422, detail=error_msg)

    # ── Step 2: Generate OTP 
    otp = auth.generate_otp()
    logger.info("Generated OTP for %s", raw_email)

    # ── Step 3: Publish to NATS 
    subject = auth.build_nats_subject(raw_email)
    payload = auth.build_payload(raw_email, otp)

    try:
        await extension.nc.publish(subject, payload)
        logger.info("OTP published to NATS subject '%s'", subject)
    except Exception as exc:
        logger.error("Failed to publish OTP to NATS: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Could not connect to messaging service. Please try again later.",
        ) from exc

    return otp_models.OTPResponse(
        message="OTP sent successfully.",
        email=raw_email,
    )