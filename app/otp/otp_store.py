import json
import time
import logging

from app import extension

logger = logging.getLogger(__name__)

OTP_KEY_TMPL = "{email}:otp"


def _key(email: str) -> str:
    return OTP_KEY_TMPL.format(email=email)


async def store_otp(email: str, otp: str, ttl_seconds: int) -> None:
    record = json.dumps({"otp": otp, "attempts": 0, "created_at": time.time()})
    await extension.rc.set(_key(email), record, ex=ttl_seconds)


async def get_otp_record(email: str):
    raw = await extension.rc.get(_key(email))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Corrupted record — treat as missing rather than ever raising.
        logger.error("Corrupted OTP record for %s — clearing it.", email)
        await extension.rc.delete(_key(email))
        return None


async def increment_attempts(email: str, record: dict) -> int:
    record["attempts"] = record.get("attempts", 0) + 1
    # keepttl=True preserves the remaining TTL, so a wrong guess doesn't
    # give the user extra time.
    await extension.rc.set(_key(email), json.dumps(record), keepttl=True)
    return record["attempts"]


async def delete_otp(email: str) -> None:
    await extension.rc.delete(_key(email))