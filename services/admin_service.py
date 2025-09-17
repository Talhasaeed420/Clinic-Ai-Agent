from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from encrypt.encryption import safe_decrypt_field
from passlib.context import CryptContext
import json

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService:

    # ================== ADMIN METHODS ==================
    @staticmethod
    async def get_admin_by_username(db: AsyncIOMotorDatabase, username: str):
        """Fetch an admin by username."""
        admin_doc = await db.admins.find_one({"username": username})
        return admin_doc

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain password."""
        return pwd_context.hash(password)

    # ================== CALL LOG METHODS ==================
    @staticmethod
    async def get_decrypted_call_log(db: AsyncIOMotorDatabase, call_log_id: str):
        try:
            obj_id = ObjectId(call_log_id)
        except:
            return None

        document = await db.callslog.find_one({"_id": obj_id})
        if not document:
            return None

        decrypted_document = document.copy()
        if "body" in decrypted_document and isinstance(decrypted_document["body"], dict):
            decrypted_document["body"] = AdminService._decrypt_payload(decrypted_document["body"])

        return decrypted_document

    @staticmethod
    async def list_call_logs(db: AsyncIOMotorDatabase, limit: int = 100):
        cursor = (
            db.callslog
            .find({}, {"_id": 1, "receivedAt": 1, "email": 1})  # include email
            .sort("receivedAt", -1)
            .limit(limit)
        )
        call_logs_list = await cursor.to_list(length=limit)
        for log in call_logs_list:
            log["_id"] = str(log["_id"])
        return call_logs_list

    # ================== CHAT METHODS ==================
    @staticmethod
    async def get_decrypted_chat(db: AsyncIOMotorDatabase, chat_id: str):
        try:
            obj_id = ObjectId(chat_id)
        except:
            return None

        document = await db.chats.find_one(
            {"_id": obj_id},
            {
                "_id": 1,
                "user_id": 1,
                "email": 1,
                "created_at": 1,
                "updated_at": 1,
                "messages": 1,
            },
        )
        if not document:
            return None

        decrypted_document = document.copy()
        if "messages" in decrypted_document and isinstance(decrypted_document["messages"], list):
            decrypted_messages = []
            for encrypted_message in decrypted_document["messages"]:
                decrypted_message_str = safe_decrypt_field(encrypted_message)
                try:
                    message_dict = json.loads(decrypted_message_str)
                    decrypted_messages.append(message_dict)
                except (json.JSONDecodeError, TypeError):
                    decrypted_messages.append(decrypted_message_str)
            decrypted_document["messages"] = decrypted_messages

        return decrypted_document

    @staticmethod
    async def list_chats(db: AsyncIOMotorDatabase, limit: int = 100):
        cursor = (
            db.chats.find(
                {},
                {
                    "_id": 1,
                    "user_id": 1,
                    "email": 1,  # ✅ include email
                    "created_at": 1,
                    "updated_at": 1,
                    "message_count": {"$size": "$messages"},
                },
            )
            .sort("updated_at", -1)
            .limit(limit)
        )

        chats_list = await cursor.to_list(length=limit)
        for chat in chats_list:
            chat["_id"] = str(chat["_id"])
        return chats_list

    # ================== APPOINTMENT METHODS ==================
    @staticmethod
    async def get_decrypted_appointment(db: AsyncIOMotorDatabase, appointment_id: str):
        try:
            obj_id = ObjectId(appointment_id)
        except:
            return None

        document = await db.appointments.find_one({"_id": obj_id})
        if not document:
            return None

        decrypted_document = document.copy()
        sensitive_fields = ["patient_email", "patient_phone", "patient_address"]
        for field in sensitive_fields:
            if field in decrypted_document:
                decrypted_document[field] = safe_decrypt_field(decrypted_document[field])

        return decrypted_document

    @staticmethod
    async def list_appointments(db: AsyncIOMotorDatabase, limit: int = 100):
        cursor = (
            db.appointments.find(
                {},
                {
                    "_id": 1,
                    "patient_name": 1,
                    "doctor_name": 1,
                    "patient_email": 1,  
                    "appointment_time": 1,
                    "created_at": 1,
                },
            )
            .sort("appointment_time", -1)
            .limit(limit)
        )

        appointments_list = await cursor.to_list(length=limit)
        for appointment in appointments_list:
            appointment["_id"] = str(appointment["_id"])
        return appointments_list

    # ================== HELPER METHODS ==================
    @staticmethod
    def _decrypt_payload(encrypted_payload: dict) -> dict:
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
