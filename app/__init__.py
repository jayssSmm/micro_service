from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes.send_otp import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from app.extension import connect_nats, close_nats

load_dotenv()


def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await connect_nats()
        yield
        await close_nats()

    app = FastAPI(lifespan=lifespan)
    app.include_router(auth_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app