# worker.py
import app.extension as extension
import json
import logging

logger = logging.getLogger(__name__)

async def start_worker(subject: str, callback) -> None:
    async def _handler(msg):
        try:
            payload = json.loads(msg.data.decode())
            await callback(payload)
        except json.JSONDecodeError:
            logger.error("Bad JSON on subject=%s: %r", msg.subject, msg.data[:200])
        except Exception:
            logger.exception("Unhandled error processing subject=%s", msg.subject)

    await extension.nc.subscribe(subject, cb=_handler)