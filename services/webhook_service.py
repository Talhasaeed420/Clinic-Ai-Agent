from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.querybuilders import AppointmentQuery
from utils.formatters import correct_number
from utils.dateparse import parse_datetime
from models.clinic import Appointment
from services.appointment_service import AppointmentService
import httpx
import os
from datetime import datetime, timezone
import json
import logging

from encrypt.encryption import encrypt_field  # 🔒

# Configure logging
logger = logging.getLogger(__name__)

MAKE_SMS_WEBHOOK_URL = os.getenv("MAKE_SMS_WEBHOOK_URL")
MAKE_BOOKING_WEBHOOK_URL = os.getenv("MAKE_BOOKING_WEBHOOK_URL")


class WebhookService:
    """Handle VAPI webhooks, encrypt sensitive fields, and forward data."""

    # ---------- ENCRYPT HELPERS ----------
    @staticmethod
    def _encrypt_value(value):
        if value is None:
            return None
        try:
            serialized = json.dumps(value)
        except Exception:
            serialized = str(value)
        return encrypt_field(serialized)

    @staticmethod
    def _encrypt_message_block(message: dict) -> dict:
        if not message:
            return message
        for field in ["message", "content", "summary", "transcript", "cost", "costs", "customer"]:
            if field in message and message[field] is not None:
                message[field] = WebhookService._encrypt_value(message[field])
        return message

    @staticmethod
    def encrypt_body(body: dict) -> dict:
        if not body or "message" not in body:
            return body

        msg = body["message"]

        # top-level
        for field in ["summary", "transcript", "costBreakdown", "cost", "costs", "customer"]:
            if field in msg:
                msg[field] = WebhookService._encrypt_value(msg[field])

        # analysis
        if "analysis" in msg:
            for field in ["summary", "transcript", "costBreakdown", "cost", "costs", "customer"]:
                if field in msg["analysis"]:
                    msg["analysis"][field] = WebhookService._encrypt_value(msg["analysis"][field])

        # artifact
        if "artifact" in msg:
            for field in ["summary", "transcript", "costBreakdown", "cost", "costs", "customer"]:
                if field in msg["artifact"]:
                    msg["artifact"][field] = WebhookService._encrypt_value(msg["artifact"][field])
            if "messages" in msg["artifact"]:
                msg["artifact"]["messages"] = [
                    WebhookService._encrypt_message_block(m) for m in msg["artifact"]["messages"]
                ]
            if "messagesOpenAIFormatted" in msg["artifact"]:
                msg["artifact"]["messagesOpenAIFormatted"] = [
                    WebhookService._encrypt_message_block(m) for m in msg["artifact"]["messagesOpenAIFormatted"]
                ]

        # messages array
        if "messages" in msg:
            msg["messages"] = [
                WebhookService._encrypt_message_block(m) for m in msg["messages"]
            ]

        # conversation
        if "conversation" in msg:
            msg["conversation"] = [
                WebhookService._encrypt_message_block(m) for m in msg["conversation"]
            ]

        return body

    # ---------- SAVE HELPERS ----------
    @staticmethod
    async def save_call_log(db: AsyncIOMotorDatabase, body: dict, call_id: str, email: str = None):
        """Save encrypted webhook data with call duration in callslog"""
        encrypted_body = WebhookService.encrypt_body(body)
        message = body.get("message", {})

        duration_seconds = message.get("durationSeconds") or message.get("duration") or 0
        duration_minutes = round(duration_seconds / 60, 2) if duration_seconds else 0.0

        await db.callslog.insert_one(
            {
                "body": encrypted_body,
                "receivedAt": datetime.utcnow(),
                "call_duration_seconds": duration_seconds,
                "call_duration_minutes": duration_minutes,
                "call_id": call_id,
                "email": email  # 👈 save caller email
            }
        )
        logger.info(f"Saved call log for call_id: {call_id}, email: {email}")

    @staticmethod
    async def save_call_start(db: AsyncIOMotorDatabase, call_id: str, email: str, user_name: str = None, user_id: str = None):
        """Save call start data including email for later retrieval"""
        try:
            await db.call_starts.insert_one(
                {
                    "call_id": call_id,
                    "email": email,
                    "user_name": user_name,
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }
            )
            logger.info(f"Saved call start data for call_id: {call_id}, email: {email}")
        except Exception as e:
            logger.error(f"Error saving call start data for call_id: {call_id}: {str(e)}")
            raise

    # ---------- MAIN HANDLERS ----------
    @staticmethod
    async def handle_end_of_call(db: AsyncIOMotorDatabase, body: dict):
        try:
            logger.info(f"Full VAPI webhook payload: {json.dumps(body, indent=2)}")
            message = body.get("message", {})
            if message.get("type") != "end-of-call-report":
                return AppointmentQuery.generic_success("Webhook event not handled", {"status": "ignored"})

            # Extract call_id (assumes VAPI payload has it at message.call.id)
            call_id = message.get("call", {}).get("id") or body.get("call_id")
            if not call_id:
                return AppointmentQuery.error("Missing call_id in payload", status="error")

            # Retrieve email from saved call start data, payload, metadata, or call_start_data
            call_start_data = await db.call_starts.find_one({"call_id": call_id})
            email = (
                call_start_data.get("email") if call_start_data
                else body.get("email") or message.get("email") or 
                message.get("metadata", {}).get("user_email") or 
                body.get("call_start_data", {}).get("email")
            )
            if not email:
                logger.warning(f"No email found for call_id: {call_id}. Metadata: {message.get('metadata', {})}")

            # Save into callslog
            await WebhookService.save_call_log(db, body, call_id, email=email)

            # Find matching appointment by call_id and update with duration if it exists
            existing_apt = await db.appointments.find_one({"call_id": call_id})
            if existing_apt:
                duration_seconds = message.get("durationSeconds") or message.get("duration") or 0
                duration_minutes = round(duration_seconds / 60, 2) if duration_seconds else 0.0

                await db.appointments.update_one(
                    {"call_id": call_id},
                    {"$set": {
                        "call_duration_seconds": duration_seconds,
                        "call_duration_minutes": duration_minutes
                    }}
                )

                # Push to Make.com with duration and email for call-based bookings
                await WebhookService.push_booking_to_make({
                    "patient_email": email or existing_apt.get("patient_email"),
                    "patient_name": existing_apt.get("patient_name"),
                    "doctor_name": existing_apt.get("doctor_name"),
                    "appointment_time": existing_apt.get("appointment_time").isoformat()
                        if existing_apt.get("appointment_time") else None,
                    "source": existing_apt.get("source"),
                    "call_duration_minutes": duration_minutes
                })

            return AppointmentQuery.generic_success("Webhook processed & appointment updated if exists")
        except Exception as e:
            logger.error(f"Error processing end-of-call webhook for call_id: {call_id}: {str(e)}")
            return AppointmentQuery.error(f"Processing error: {str(e)}", status="error")

    @staticmethod
    async def handle_call_start(db: AsyncIOMotorDatabase, body: dict):
        """Handle call start webhook to save email and metadata"""
        try:
            call_id = body.get("call_id")
            email = body.get("email")
            user_name = body.get("user_name", "")
            user_id = body.get("user_id", "")

            if not call_id or not email:
                return AppointmentQuery.error("Missing call_id or email in call start payload", status="error")

            await WebhookService.save_call_start(db, call_id, email, user_name, user_id)

            return AppointmentQuery.generic_success("Call start data saved successfully")
        except Exception as e:
            logger.exception(f"Error handling call start: {str(e)}")
            return AppointmentQuery.error(f"Processing error: {str(e)}", status="error")

    @staticmethod
    async def handle_tool_call(db: AsyncIOMotorDatabase, body: dict):
        try:
            logger.info(f"Processing tool call payload: {json.dumps(body, indent=2)}")

            if not body.get("message", {}).get("toolCalls"):
                return AppointmentQuery.error("Missing or empty toolCalls in payload", status="error")

            tool_call_data = body["message"]["toolCalls"][0]["function"]
            function_name = tool_call_data["name"]
            parameters = tool_call_data["arguments"]
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid arguments JSON: {str(e)}")
                    return AppointmentQuery.error(f"Invalid arguments JSON: {str(e)}", status="error")

            if function_name != "book_appointment":
                return AppointmentQuery.error("This webhook event was not handled.", status="error")

            call_id = body["message"].get("call", {}).get("id") or body["message"].get("chat", {}).get("id")
            if not call_id:
                return AppointmentQuery.error("Missing call_id or chat_id in payload", status="error")

            if body["message"].get("call"):
                source = "book_call"
            elif body["message"].get("chat"):
                source = "book_chat"
            else:
                source = "book_unknown"

            parameters["source"] = source
            parameters["call_id"] = call_id

            if "appointment_time" in parameters and parameters["appointment_time"]:
                try:
                    parameters["appointment_time"] = parse_datetime(parameters["appointment_time"])
                except Exception as e:
                    logger.error(f"Failed to parse appointment_time: {str(e)}")
                    return AppointmentQuery.error(f"Invalid appointment_time: {str(e)}", status="error")
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            required_fields = ["patient_name", "doctor_name"]
            missing = [f for f in required_fields if f not in parameters or not parameters[f]]
            if missing:
                return AppointmentQuery.error(f"Missing required fields: {', '.join(missing)}", status="error")

            existing = await AppointmentService.find_duplicate(
                db, parameters.get("patient_name"), parameters.get("doctor_name"), parameters.get("appointment_time")
            )
            if existing:
                return AppointmentQuery.error("Appointment already exists", status="error")

            appointment = Appointment(**parameters)
            inserted = await AppointmentService.create_appointment(db, appointment)

            call_duration_minutes = 0.0
            call_duration_seconds = 0
            existing_log = await db.callslog.find_one({"call_id": call_id})
            if existing_log and source == "book_call":
                call_duration_minutes = existing_log.get("call_duration_minutes", 0.0)
                call_duration_seconds = existing_log.get("call_duration_seconds", 0)

            await db.appointments.update_one(
                {"call_id": call_id},
                {"$set": {
                    "call_duration_seconds": call_duration_seconds,
                    "call_duration_minutes": call_duration_minutes
                }}
            )

            booking_data = {
                "patient_email": parameters.get("patient_email") or (existing_log.get("patient_email") if existing_log else None),
                "patient_name": inserted.get("patient_name"),
                "doctor_name": inserted.get("doctor_name"),
                "appointment_time": inserted.get("appointment_time").isoformat() if inserted.get("appointment_time") else None,
                "source": inserted.get("source"),
            }
            if source == "book_call":
                booking_data["call_duration_minutes"] = call_duration_minutes

            await WebhookService.push_booking_to_make(booking_data)

            return AppointmentQuery.appointment_booked(
                inserted["patient_name"], inserted["doctor_name"], inserted["id"]
            )

        except Exception as e:
            logger.exception(f"Error in handle_tool_call: {str(e)}")
            return AppointmentQuery.error(f"Processing error: {str(e)}", status="error")

    # ---------- EXTERNAL PUSH HELPERS ----------
    @staticmethod
    def correct_number(number: str):
        return correct_number(number)

    @staticmethod
    async def push_sms_to_make(phone: str):
        if MAKE_SMS_WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                await client.post(MAKE_SMS_WEBHOOK_URL, json={"patient_phone": phone})

    @staticmethod
    async def push_booking_to_make(data: dict):
        if MAKE_BOOKING_WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                await client.post(MAKE_BOOKING_WEBHOOK_URL, json=data)