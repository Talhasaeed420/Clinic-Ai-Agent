import os
import logging
logger = logging.getLogger(__name__)
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# --------------------------------
# Logging Configuration
# --------------------------------
LOG_FILE = "app.log"

logging.basicConfig(
    level=logging.INFO,  # log INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --------------------------------
# Environment Variables
# --------------------------------
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")  # ✅ Use from .env instead of hardcoding

if not MONGODB_URI:
    logger.critical(" MONGODB_URI is not set in .env")
    raise ValueError(" MONGODB_URI is not set in .env")

if not DB_NAME:
    logger.critical(" DB_NAME is not set in .env")
    raise ValueError(" DB_NAME is not set in .env")

# --------------------------------
# MongoDB Connection (Lifespan)
# --------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.mongodb_client = AsyncIOMotorClient(MONGODB_URI)
        app.mongodb = app.mongodb_client[DB_NAME]
        logger.info(f"MongoDB connected to {DB_NAME}")
        yield
    except Exception as e:
        logger.exception(f" MongoDB connection error: {e}")
        raise
    finally:
        app.mongodb_client.close()
        logger.warning(" MongoDB disconnected.")

# --------------------------------
# Dependency
# --------------------------------
async def get_database(request: Request):
    return request.app.mongodb
