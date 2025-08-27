from fastapi import APIRouter, Request, HTTPException, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
from database import get_database
from typing import List
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from scripts.sync_vapi_assistant import sync_assistant
import json
from datetime import datetime, timezone
from constants.constant import ERRORS

router = APIRouter()
logger = logging.getLogger("appointments")

# ---------------- GETTING ASSISTANT CONFIG ---------------- #
@router.get("/bot-config")
async def get_assistant_config(request: Request):
    db = await get_database(request)
    config = await db.bot_configs.find_one({}, {"_id": 0})
    if not config:
        logger.warning("Assistant configuration not found")
        raise HTTPException(status_code=404, detail="Assistant configuration not found")

    logger.info("Sending config to Vapi: %s", json.dumps(config, indent=2))
    return config


# ---------------- UPDATE BOT CONFIG ---------------- #
@router.post("/bot-config/update")
async def update_assistant_config(request: Request, new_config: dict = Body(...)):
    db = await get_database(request)

    existing = await db.bot_configs.find_one({}, {"_id": 0})
    if not existing:
        logger.warning("Assistant configuration not found during update")
        raise HTTPException(status_code=404, detail="Assistant configuration not found")

    merged_config = {**existing, **new_config}
    await db.bot_configs.update_one({}, {"$set": merged_config})
    updated = await db.bot_configs.find_one({}, {"_id": 0})

    logger.info("Updated config: %s", json.dumps(updated, indent=2))
    return {"message": "✅ Config updated successfully", "updated_config": updated}


# ---------------- SYNC ASSISTANT ---------------- #
@router.post("/sync-assistant")
async def sync_assistant_endpoint():
    try:
        result = await run_in_threadpool(sync_assistant)
        logger.info("Assistant synced successfully")
        return {"status": "ok", "assistant": result}
    except Exception:
        logger.exception("Error syncing assistant")
        return {"status": "error", "detail": "Failed to sync assistant"}


# ---------------- GET VAPI OPTIONS ---------------- #
@router.get("/vapi/options")
async def get_vapi_options(db: AsyncIOMotorDatabase = Depends(get_database)):
    collection = db["vapi-options"]
    options_cursor = collection.find({})
    options = await options_cursor.to_list(length=None)

    if not options:
        logger.warning("No options found in vapi-options collection")
        return {"status": "error", "message": "No options found in database"}

    for opt in options:
        opt.pop("_id", None)

    logger.info("Fetched %d vapi options", len(options))
    return {"status": "ok", "data": options}
