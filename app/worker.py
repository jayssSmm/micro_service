import json

from extension import nc

async def start_worker(subject, callback):
    subscription = await nc.subscribe(subject)

    async for i in subscription.messages:
        payload = json.loads(
            i.data.decode()
        )

        await callable(payload)