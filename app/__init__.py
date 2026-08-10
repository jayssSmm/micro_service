from fastapi import FastAPI
from dotenv import load_dotenv
from auth import router as auth_router

from contextlib import asynccontextmanager
from extension import connect_nats, close_nats

load_dotenv()

def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await connect_nats
        yield
        await close_nats

    app = FastAPI(lifespan=lifespan)
    app.include_router(auth_router)

    return app