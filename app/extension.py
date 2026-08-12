import logging

import nats
import redis.asyncio as redis

from app import config

logger = logging.getLogger(__name__)

nc = None
rc = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)


async def connect_nats():
    global nc
    try:
        nc = await nats.connect(config.NATS_URL, connect_timeout=5)
        logger.info("Connected to NATS at %s", config.NATS_URL)
    except Exception:
        logger.exception("Could not connect to NATS at startup — falling back to direct SMTP for all sends.")
        nc = None
    return nc


async def close_nats():
    global nc
    if nc and not nc.is_closed:
        try:
            await nc.drain()
        except Exception:
            logger.exception("Error draining NATS connection")
    nc = None


def nats_available() -> bool:
    return nc is not None and not nc.is_closed