import nats
import os

nc = None
NATS_URL = os.getenv("NATS_URL")

async def connect_nats():
    global nc
    nc = await nats.connect(NATS_URL)
    return nc

async def close_nats():
    global nc
    if nc:
        await nc.drain()
        await nc.close()
        nc = None