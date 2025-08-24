from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")  # ✅ Use from .env instead of hardcoding

if not MONGODB_URI:
    raise ValueError("❌ MONGODB_URI is not set in .env")
if not DB_NAME:
    raise ValueError("❌ DB_NAME is not set in .env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URI)
    app.mongodb = app.mongodb_client[DB_NAME]
    print(f"✅ MongoDB connected to {DB_NAME}.")
    yield
    app.mongodb_client.close()
    print("❌ MongoDB disconnected.")

# Dependency to get database instance
async def get_database(request: Request):
    return request.app.mongodb
