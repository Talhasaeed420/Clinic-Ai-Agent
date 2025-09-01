import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load env
load_dotenv()

#
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")


async def save_config():
    try:
        logger.info("🚀 Starting save_config")

        if not MONGO_URI or not DB_NAME:
            logger.error("❌ Missing env vars: MONGODB_URI / DB_NAME")
            return

        # Import payload + schema
        from onetime_botconfig.assistant_config import assistant_payload
        from models.dynamic_vapi import AssistantPayload

        # Build assistant config (NO toolIds)
        assistant = assistant_payload()

        # Lowercase provider (safe cleanup)
        if "voice" in assistant and "provider" in assistant["voice"]:
            assistant["voice"]["provider"] = assistant["voice"]["provider"].lower()

        # Validate with Pydantic
        assistant_object = AssistantPayload(**assistant)
        logger.info(f"✅ Assistant validated: {assistant_object.name}")

        # Save into MongoDB
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        logger.info("✅ MongoDB connection successful")

        db = client[DB_NAME]

        # overwrite existing config with same name
        await db["bot_configs"].delete_many({"name": assistant_object.name})
        result = await db["bot_configs"].insert_one(assistant_object.dict())
        logger.info(f"✅ Inserted document with ID: {result.inserted_id}")

    except Exception as e:
        logger.exception("❌ Error saving config")


if __name__ == "__main__":
    asyncio.run(save_config())
