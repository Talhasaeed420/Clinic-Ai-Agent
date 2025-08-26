import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]


async def seed_vapi_options():
    collection = db["vapi-options"]

    existing = await collection.count_documents({})
    if existing > 0:
        print("✅ VAPI options already exist, skipping insert.")
        return

    vapi_options = {
        "voices": [
            {
                "provider": "deepgram",
                "models": ["aura-astro", "aura-vela"],
                "languages": ["en", "es", "fr"]
            },
            {
                "provider": "11labs",
                "models": ["multilingual-v2", "english-v1"],
                "languages": ["en", "de", "it", "pt"]
            },
            {
                "provider": "openai",
                "models": ["gpt-4o-mini-tts", "gpt-4o-tts"],
                "languages": ["en", "ja", "zh"]
            }
        ],
        "transcribers": [
            {
                "provider": "deepgram",
                "models": ["nova-2", "nova-2-phonecall"],
                "languages": ["en", "es", "hi"]
            },
            {
                "provider": "openai",
                "models": ["gpt-4o-mini-transcribe", "whisper-1"],
                "languages": ["en", "fr", "de"]
            },
            {
                "provider": "assemblyai",
                "models": ["default", "phonecall"],
                "languages": ["en"]
            }
        ]
    }

    await collection.insert_one(vapi_options)
    print("✅ VAPI options inserted successfully.")


if __name__ == "__main__":
    asyncio.run(seed_vapi_options())
