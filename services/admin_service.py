# services/admin_service.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from encrypt.encryption import safe_decrypt_field
import json

class AdminService:

    # ========== CALL LOG METHODS ==========
    @staticmethod
    async def get_decrypted_call_log(db: AsyncIOMotorDatabase, call_log_id: str):
        """Fetch a call log by ID and decrypt its sensitive fields."""
        try:
            obj_id = ObjectId(call_log_id)
        except:
            return None

        document = await db.callslog.find_one({"_id": obj_id})
        if not document:
            return None

        decrypted_document = document.copy()
        if 'body' in decrypted_document and isinstance(decrypted_document['body'], dict):
            decrypted_document['body'] = AdminService._decrypt_payload(decrypted_document['body'])

        return decrypted_document

    @staticmethod
    async def list_call_logs(db: AsyncIOMotorDatabase, limit: int = 100):
        """Get a list of all call logs (just their IDs and timestamps)."""
        cursor = db.callslog.find({}, {
            "_id": 1,
            "receivedAt": 1
        }).sort("receivedAt", -1).limit(limit)
        
        call_logs_list = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON response
        for log in call_logs_list:
            log["_id"] = str(log["_id"])
            
        return call_logs_list

    # ========== CHAT METHODS ==========
    @staticmethod
    async def get_decrypted_chat(db: AsyncIOMotorDatabase, chat_id: str):
        """Fetch a chat by ID and decrypt its message history."""
        try:
            obj_id = ObjectId(chat_id)
        except:
            return None

        document = await db.chats.find_one({"_id": obj_id})
        if not document:
            return None

        decrypted_document = document.copy()
        
        # Decrypt all messages in the chat
        if 'messages' in decrypted_document and isinstance(decrypted_document['messages'], list):
            decrypted_messages = []
            for encrypted_message in decrypted_document['messages']:
                # Decrypt the message string
                decrypted_message_str = safe_decrypt_field(encrypted_message)
                try:
                    # Parse the JSON string back to a Python dictionary
                    message_dict = json.loads(decrypted_message_str)
                    decrypted_messages.append(message_dict)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, just add the decrypted string
                    decrypted_messages.append(decrypted_message_str)
            
            decrypted_document['messages'] = decrypted_messages

        return decrypted_document

    @staticmethod
    async def list_chats(db: AsyncIOMotorDatabase, limit: int = 100):
        """Get a list of all chats (just their IDs and basic info)."""
        cursor = db.chats.find({}, {
            "_id": 1,
            "user_id": 1,
            "created_at": 1,
            "updated_at": 1,
            "message_count": {"$size": "$messages"}  # Count number of messages
        }).sort("updated_at", -1).limit(limit)
        
        chats_list = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON response
        for chat in chats_list:
            chat["_id"] = str(chat["_id"])
            
        return chats_list

    # ========== APPOINTMENT METHODS ==========
    @staticmethod
    async def get_decrypted_appointment(db: AsyncIOMotorDatabase, appointment_id: str):
        """Fetch an appointment by ID and decrypt its sensitive fields."""
        try:
            obj_id = ObjectId(appointment_id)
        except:
            return None

        document = await db.appointments.find_one({"_id": obj_id})
        if not document:
            return None

        decrypted_document = document.copy()
        # Decrypt specific appointment fields
        sensitive_fields = ["patient_email", "patient_phone", "patient_address"]
        for field in sensitive_fields:
            if field in decrypted_document:
                decrypted_document[field] = safe_decrypt_field(decrypted_document[field])

        return decrypted_document

    @staticmethod
    async def list_appointments(db: AsyncIOMotorDatabase, limit: int = 100):
        """Get a list of all appointments (just their IDs and basic info)."""
        cursor = db.appointments.find({}, {
            "_id": 1,
            "patient_name": 1,
            "doctor_name": 1,
            "appointment_time": 1,
            "created_at": 1
        }).sort("appointment_time", -1).limit(limit)
        
        appointments_list = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON response
        for appointment in appointments_list:
            appointment["_id"] = str(appointment["_id"])
            
        return appointments_list

    # ========== HELPER METHODS ==========
    @staticmethod
    def _decrypt_payload(encrypted_payload: dict) -> dict:
        """Recursively traverse the payload and decrypt all encrypted strings."""
        if not isinstance(encrypted_payload, dict):
            return encrypted_payload

        decrypted_dict = {}
        for key, value in encrypted_payload.items():
            if key in ["summary", "transcript", "content", "message", "costBreakdown"] and isinstance(value, str):
                decrypted_value = safe_decrypt_field(value)
                try:
                    decrypted_dict[key] = json.loads(decrypted_value)
                except (json.JSONDecodeError, TypeError):
                    decrypted_dict[key] = decrypted_value
            elif isinstance(value, dict):
                decrypted_dict[key] = AdminService._decrypt_payload(value)
            elif isinstance(value, list):
                decrypted_dict[key] = [AdminService._decrypt_payload(item) for item in value]
            else:
                decrypted_dict[key] = value

        return decrypted_dict