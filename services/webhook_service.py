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

from encrypt.encryption import encrypt_field  # 🔒

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
    async def save_call_log(db: AsyncIOMotorDatabase, body: dict, call_id: str):
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
                "call_id": call_id,  # Save call_id for linking
            }
        )

    # ---------- MAIN HANDLERS ----------
    @staticmethod
    async def handle_end_of_call(db: AsyncIOMotorDatabase, body: dict):
        message = body.get("message", {})
        if message.get("type") != "end-of-call-report":
            return AppointmentQuery.generic_success("Webhook event not handled", {"status": "ignored"})

        # Extract call_id (assumes VAPI payload has it at message.call.id)
        call_id = message.get("call", {}).get("id")
        if not call_id:
            return AppointmentQuery.error("Missing call_id in payload", status="error")

        # Save into callslog
        await WebhookService.save_call_log(db, body, call_id)

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

            # Push to Make.com now that we have both appointment and duration
            await WebhookService.push_booking_to_make({
                "patient_email": existing_apt.get("patient_email"),
                "patient_name": existing_apt.get("patient_name"),
                "doctor_name": existing_apt.get("doctor_name"),
                "appointment_time": existing_apt.get("appointment_time").isoformat()
                if existing_apt.get("appointment_time") else None,
                "source": existing_apt.get("source"),
                "call_duration_minutes": duration_minutes
            })

        return AppointmentQuery.generic_success("Webhook processed & appointment updated if exists")

    @staticmethod
    async def handle_tool_call(db: AsyncIOMotorDatabase, body: dict):
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        if function_name != "book_appointment":
            return AppointmentQuery.error("This webhook event was not handled.", status="error")

        # Extract call_id (assumes VAPI payload has it at message.call.id)
        call_id = body["message"].get("call", {}).get("id")
        if not call_id:
            return AppointmentQuery.error("Missing call_id in payload", status="error")

        # Detect source
        if body["message"].get("call"):
            source = "book_call"
        elif body["message"].get("chat"):
            source = "book_chat"
        else:
            source = "book_unknown"

        parameters["source"] = source
        parameters["call_id"] = call_id  # Add to parameters for saving

        # Parse appointment time
        if "appointment_time" in parameters:
            parameters["appointment_time"] = parse_datetime(parameters["appointment_time"])
        else:
            parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        # Check duplicate
        existing = await AppointmentService.find_duplicate(
            db, parameters.get("patient_name"), parameters.get("doctor_name"), parameters.get("appointment_time")
        )
        if existing:
            return AppointmentQuery.error("Appointment already exists", status="error")

        # Create appointment
        appointment = Appointment(**parameters)
        inserted = await AppointmentService.create_appointment(db, appointment)

        # Check if call log (with duration) already exists (for out-of-order webhooks)
        existing_log = await db.callslog.find_one({"call_id": call_id})
        if existing_log:
            # Update appointment with duration from log
            await db.appointments.update_one(
                {"call_id": call_id},
                {"$set": {
                    "call_duration_seconds": existing_log["call_duration_seconds"],
                    "call_duration_minutes": existing_log["call_duration_minutes"]
                }}
            )

            # Push to Make.com now that we have both
            await WebhookService.push_booking_to_make({
                "patient_email": inserted.get("patient_email"),
                "patient_name": inserted.get("patient_name"),
                "doctor_name": inserted.get("doctor_name"),
                "appointment_time": inserted.get("appointment_time").isoformat()
                if inserted.get("appointment_time") else None,
                "source": inserted.get("source"),
                "call_duration_minutes": existing_log["call_duration_minutes"]
            })

        # Note: If no log yet, don't push here—handle_end_of_call will do it when it arrives
        return AppointmentQuery.appointment_booked(
            inserted["patient_name"], inserted["doctor_name"], inserted["id"]
        )

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