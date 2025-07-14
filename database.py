from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "voicebot"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URI)
    app.mongodb = app.mongodb_client[DB_NAME]
    print("MongoDB connected.")
    yield
    app.mongodb_client.close()
    print("MongoDB disconnected.")

async def get_database(request: Request):
    return request.app.mongodb
