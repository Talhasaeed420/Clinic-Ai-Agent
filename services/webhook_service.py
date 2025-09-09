# services/webhook_service.py
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
        for field in ["message", "content", "summary", "transcript","cost","costs","customer"]:
            if field in message and message[field] is not None:
                message[field] = WebhookService._encrypt_value(message[field])
        return message

    @staticmethod
    def encrypt_body(body: dict) -> dict:
        if not body or "message" not in body:
            return body

        msg = body["message"]

        # top-level
        for field in ["summary", "transcript", "costBreakdown","cost","costs","customer"]:
            if field in msg:
                msg[field] = WebhookService._encrypt_value(msg[field])

        # analysis
        if "analysis" in msg:
            for field in ["summary", "transcript", "costBreakdown","cost","costs","customer"]:
                if field in msg["analysis"]:
                    msg["analysis"][field] = WebhookService._encrypt_value(msg["analysis"][field])

        # artifact
        if "artifact" in msg:
            for field in ["summary", "transcript", "costBreakdown","cost","costs","customer"]:
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
    async def save_call_log(db: AsyncIOMotorDatabase, body: dict):
        """Save encrypted webhook data only in callslog"""
        encrypted_body = WebhookService.encrypt_body(body)
        await db.callslog.insert_one(
            {"body": encrypted_body, "receivedAt": datetime.utcnow()}
        )

    # ---------- MAIN HANDLERS ----------
    @staticmethod
    async def handle_end_of_call(db: AsyncIOMotorDatabase, body: dict):
        message = body.get("message", {})
        if message.get("type") != "end-of-call-report":
            return AppointmentQuery.generic_success("Webhook event not handled", {"status": "ignored"})

        await WebhookService.save_call_log(db, body)  # ✅ Only saving to callslo

        return AppointmentQuery.generic_success("Webhook processed")

    @staticmethod
    async def handle_tool_call(db: AsyncIOMotorDatabase, body: dict):
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        if function_name != "book_appointment":
            return AppointmentQuery.error("This webhook event was not handled.", status="error")

        # parse appointment_time
        if "appointment_time" in parameters:
            parameters["appointment_time"] = parse_datetime(parameters["appointment_time"])
        else:
            parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        # check for duplicate
        existing = await AppointmentService.find_duplicate(
            db, parameters["patient_name"], parameters["doctor_name"], parameters["appointment_time"]
        )
        if existing:
            return AppointmentQuery.error("Appointment already exists", status="error")

        # 🔒 encrypt email BEFORE creating the appointment
        if "patient_email" in parameters and parameters["patient_email"]:
            parameters["patient_email"] = WebhookService._encrypt_value(parameters["patient_email"])

        # create appointment
        appointment = Appointment(**parameters)
        inserted = await AppointmentService.create_appointment(db, appointment)

        if inserted:
            # push encrypted email externally
            await WebhookService.push_booking_to_make({
                "patient_email": inserted.get("patient_email"),
                "patient_name": inserted.get("patient_name"),
                "doctor_name": inserted.get("doctor_name"),
                "appointment_time": inserted.get("appointment_time").isoformat() if inserted.get("appointment_time") else None,
            })

            # optionally save appointment in callslog if needed
           # await WebhookService.save_call_log(db, {"message": tool_call_data})

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
