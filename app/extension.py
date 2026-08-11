import nats
import os
from dotenv import load_dotenv

load_dotenv()

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
        nc = None

rc = None
NATS_URL = os.getenv("NATS_URL")

async def connect_nats():
    global nc, rc
    nc = await nats.connect(NATS_URL)