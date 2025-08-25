import os
from dotenv import load_dotenv

load_dotenv()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
def tools_payloads():
    """Define tool configs (VAPI schema compliant)."""
    return [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book a clinic appointment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "Name of the patient"},
                        "doctor_name": {"type": "string", "description": "Name of the doctor"},
                        "appointment_time": {"type": "string", "description": "Time of the appointment (ISO 8601 or natural language)"}
                    },
                    "required": ["patient_name", "doctor_name", "appointment_time"]
                }
            },
            "server": { 
                "url": f"{PUBLIC_BASE_URL}/bookings"
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Check if a slot is available at a given time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_time": {"type": "string", "description": "Desired appointment time"}
                    },
                    "required": ["appointment_time"]
                }
            },
            "server": { 
                "url": f"{PUBLIC_BASE_URL}/bookings"
            }
        }
    ]



def assistant_payload(tool_ids):
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
            "model": "gpt-4o-mini",
            "toolIds": tool_ids
        },
        "server": {   # 👈 webhook lives here, not in tools
            "url": f"{PUBLIC_BASE_URL}/webhook",
        }
    }
