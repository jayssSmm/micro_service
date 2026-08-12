import nats
import os
from dotenv import load_dotenv
import redis

load_dotenv()

nc = None
rc = redis.Redis.from_url(os.getenv('REDIS_URL'))

async def connect_nats():
    global nc
    nc = await nats.connect(os.getenv("NATS_URL"))
    return nc

async def close_nats():
    global nc
    if nc:
        await nc.drain()
        nc = None
