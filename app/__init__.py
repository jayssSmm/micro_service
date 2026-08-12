import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import extension, config, worker
from app.routes.send_otp import router as send_otp_router
from app.routes.verify_otp import router as verify_otp_router

logger = logging.getLogger(__name__)


def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await extension.connect_nats()
        await worker.start_workers()
        yield
        await worker.stop_workers()
        await extension.close_nats()

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Last line of defense: whatever goes wrong, the process itself must
    # never crash — always return a JSON error instead.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})

    app.mount("/static", StaticFiles(directory="templates/static"), name="static")

    @app.get("/")
    async def index():
        return FileResponse("templates/index.html")

    app.include_router(send_otp_router)
    app.include_router(verify_otp_router)
    return app