import os
from dotenv import load_dotenv
load_dotenv()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")

def tools_payloads():
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
                        "appointment_time": {"type": "string", "description": "Time of the appointment"},
                        "reason": {"type": "string", "description": "Reason for the appointment"},
                    },
                    "required": ["patient_name", "doctor_name", "appointment_time", "reason"]
                }
            },
            "server": {
                "url": f"{PUBLIC_BASE_URL}/bookings"
            }
        }
    ]
