from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes.send_otp import router as auth_router
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import app.extension as extension

def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await extension.connect_nats()
        yield
        await extension.nc.close()

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