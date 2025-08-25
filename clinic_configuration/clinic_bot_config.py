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
    
    # Fresh config
    config = {
        "name": "clinic_assistant_bot",
        "model": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "systemPrompt": (
                "You are a friendly and helpful AI assistant for a clinic. "
                "Greet patients warmly and ask how they are feeling. Politely inquire about the name for their appointment. "
                "Help them book appointments, check doctor availability, and answer any basic questions about the clinic.\n\n"
                "Make the conversation natural, empathetic, and human-like while staying professional. "
                "Use the tools listed under tools when needed."
            ),
            "messages": [
                {
                    "role": "system",
                    "content": "Your system prompt here if needed"
                }
            ]
        },
        "voice": {
            "provider": "vapi",  
            "voiceId": "Ava",    
        },
        "transcriber": {
            "provider": "deepgram",  
            "model": "nova-2",      
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
        ]
    }
    
    result = await db.bot_configs.insert_one(config)
    return f"Deleted {delete_result.deleted_count} old config(s), inserted new config with ID: {result.inserted_id}"


async def update_clinic_bot_config(db, update: dict):
    result = await db.bot_configs.update_one(
        {"name": "clinic_assistant_bot"},
        {"$set": update}
    )

    if result.modified_count == 0:
        return "No config updated (maybe config not found?)"
    return f"Updated config with fields: {list(update.keys())}"


