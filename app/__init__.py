from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from app.routes.send_otp import router as auth_router
from contextlib import asynccontextmanager
from app.extension import connect_nats, close_nats
from config import validate
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS
import asyncio
from app.auth.auth import start_otp_worker

def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate()
        await connect_nats()
        asyncio.create_task(start_otp_worker())  # ADD THIS
        yield
        await close_nats()

    app = FastAPI(lifespan=lifespan)

    # ── CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="templates/static"), name="static")

    @app.get("/")
    async def index():
        return FileResponse("templates/index.html")

    app.include_router(auth_router)
    return app