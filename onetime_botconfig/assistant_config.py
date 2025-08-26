import os
from dotenv import load_dotenv

load_dotenv()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")

def assistant_payload():
    """Define assistant config with global webhook (/webhook)."""
    return {
        "name": "Clinic Assistant",
        "firstMessage": "Hi! I can help you book an appointment. Who am I speaking with?",
        "voice": {
            "provider": "vapi",
            "voiceId": "Cole"
        },
        "transcriber": {
            "provider": "deepgram",
            "language": "en"
        },
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini"
        },
        "server": {
            "url": f"{PUBLIC_BASE_URL}/webhook"
        }
    }
