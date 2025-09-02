from fastapi import APIRouter, Request, HTTPException, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database
from fastapi.concurrency import run_in_threadpool
from scripts.sync_vapi_assistant import sync_assistant
from constants.clinic_status import STATUS, ERRORS
import logging

router = APIRouter()
logger = logging.getLogger("appointments")

# ---------------- GETTING ASSISTANT CONFIG ---------------- #
@router.get("/bot-config")
async def get_assistant_config(request: Request):
    db = await get_database(request)
    config = await db.bot_configs.find_one({}, {"_id": 0})
    if not config:
        logger.warning("Assistant configuration not found")
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])
    logger.info("Fetched assistant config")
    return config


# ---------------- UPDATE BOT CONFIG ---------------- #
@router.post("/bot-config/update")
async def update_assistant_config(request: Request, new_config: dict = Body(...)):
    db = await get_database(request)
    existing = await db.bot_configs.find_one({}, {"_id": 0})
    if not existing:
        logger.warning("Assistant configuration not found during update")
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])

    merged_config = {**existing, **new_config}
    await db.bot_configs.update_one({}, {"$set": merged_config})
    updated = await db.bot_configs.find_one({}, {"_id": 0})
    logger.info("Assistant config updated")
    return updated


# ---------------- SYNC ASSISTANT ---------------- #
@router.post("/sync-assistant")
async def sync_assistant_endpoint():
    try:
        result = await run_in_threadpool(sync_assistant)
        logger.info("Assistant synced successfully")
        return result
    except Exception as e:
        logger.exception("Error syncing assistant: %s", e)
        raise HTTPException(status_code=500, detail="Failed to sync assistant")


# ---------------- GET VAPI OPTIONS ---------------- #
@router.get("/vapi/options")
async def get_vapi_options(db: AsyncIOMotorDatabase = Depends(get_database)):
    collection = db["vapi-options"]
    options = await collection.find({}).to_list(length=None)
    if not options:
        logger.warning("No vapi options found")
        raise HTTPException(status_code=404, detail="No options found")
    for opt in options:
        opt.pop("_id", None)
    logger.info("Fetched %d vapi options", len(options))
    return options
