from fastapi import FastAPI
from dotenv import load_dotenv
from auth import router as auth_router


load_dotenv()

def create_app():
    app = FastAPI()
    app.include_router(auth_router)

    return app