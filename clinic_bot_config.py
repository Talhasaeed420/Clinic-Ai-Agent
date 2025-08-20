from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")


async def insert_clinic_bot_config(db):
    # Delete old config
    delete_result = await db.bot_configs.delete_many({"name": "clinic_assistant_bot"})

    config = {
        "name": "clinic_assistant_bot",
        "prompt": "You are a helpful AI assistant for a clinic. Greet patients warmly, help them book appointments, check availability, and answer basic queries politely.",
        "voice": {
            "provider": "vapi",
            "voice_id": "alloy",
            "language": "en-US"
        },
        "transcriber": {
            "provider": "vapi",
            "language": "en"
        },
        "tools": [
            {
                "name": "book_appointment",
                "description": "Book an appointment for a patient at the clinic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string"},
                        "preferred_date": {"type": "string"},
                        "doctor": {"type": "string"}
                    },
                    "required": ["patient_name", "preferred_date"]
                }
            },
            {
                "name": "check_availability",
                "description": "Check a doctor's availability for a given date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["doctor", "date"]
                }
            }
        ],
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer 872a3945-34b0-40cb-8e90-5491d7c95f70"
        }
    }

    result = await db.bot_configs.insert_one(config)
    return f"Deleted {delete_result.deleted_count} old config(s), inserted new config with ID: {result.inserted_id}"


async def update_clinic_bot_config(db, new_config: dict):
    result = await db.bot_configs.update_one(
        {"name": "clinic_assistant_bot"},  # filter by bot name
        {"$set": new_config}
    )

    if result.matched_count == 0:
        return "No existing clinic bot config found to update."
    return f"Updated clinic bot config. Modified count: {result.modified_count}"
