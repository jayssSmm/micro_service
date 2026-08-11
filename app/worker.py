import json
from app.extension import nc

async def start_worker(subject: str, callback) -> None:
    async def _handler(msg):
        payload = json.loads(msg.data.decode())
        await callback(payload)

    await nc.subscribe(subject, cb=_handler)  # FIX: pass cb= directly