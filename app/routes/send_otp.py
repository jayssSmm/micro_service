import nats
from fastapi import APIRouter, HTTPException
from models import otp_models
from auth import auth
from extensions import NATS_URL

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/send-otp", response_model=otp_models.OTPResponse)
async def send_otp(request: otp_models.OTPRequest):
    """
    1. Receive email from the frontend.
    2. Validate email format.
    3. Generate a 6-digit OTP.
    4. Publish it to NATS on subject  otp.<email>
       with payload  { email, otp, timestamp }.
    5. Return a success message (OTP is NOT echoed back to the client).
    """
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
        nc = await nats.connect(NATS_URL)
        await nc.publish(subject, payload)
        await nc.flush()          # make sure the message is actually sent
        await nc.close()
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