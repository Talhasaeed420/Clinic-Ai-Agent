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

MAKE_SMS_WEBHOOK_URL = os.getenv("MAKE_SMS_WEBHOOK_URL")
MAKE_BOOKING_WEBHOOK_URL = os.getenv("MAKE_BOOKING_WEBHOOK_URL")


class WebhookService:
    """Handle VAPI webhooks and tool calls."""

    @staticmethod
    async def save_call_log(db: AsyncIOMotorDatabase, body: dict):
        await db.callslog.insert_one({"body": body, "receivedAt": datetime.utcnow()})

    @staticmethod
    async def save_call_data(db: AsyncIOMotorDatabase, call_data: dict):
        await db.calls.insert_one(call_data)

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

    @staticmethod
    async def handle_end_of_call(db: AsyncIOMotorDatabase, body: dict):
        message = body.get("message", {})
        if message.get("type") != "end-of-call-report":
            return AppointmentQuery.generic_success("Webhook event not handled", {"status": "ignored"})

        call_id = body.get("call", {}).get("id")
        await WebhookService.save_call_log(db, body)

        if call_id:
            await db.calls.delete_one({"call.id": call_id})

        customer_number = message.get("customer", {}).get("number")
        corrected_number = WebhookService.correct_number(customer_number) if customer_number else None

        call_data = {
            "timestamp": message.get("timestamp"),
            "type": message.get("type"),
            "analysis": message.get("analysis", {}),
            "artifact": message.get("artifact", {}),
            "performanceMetrics": body.get("performanceMetrics", {}),
            "call": body.get("call", {}),
            "assistant": body.get("assistant", {}),
            "customer_number_original": customer_number,
            "customer_number_corrected": corrected_number,
            "updatedAt": datetime.utcnow(),
        }

        await WebhookService.save_call_data(db, call_data)

        if corrected_number:
            await WebhookService.push_sms_to_make(corrected_number)

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

        if "appointment_time" in parameters:
            parameters["appointment_time"] = parse_datetime(parameters["appointment_time"])
        else:
            parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        existing = await AppointmentService.find_duplicate(
            db, parameters["patient_name"], parameters["doctor_name"], parameters["appointment_time"]
        )

        if existing:
            return AppointmentQuery.error("Appointment already exists", status="error")

        appointment = Appointment(**parameters)
        inserted = await AppointmentService.create_appointment(db, appointment)

        if inserted:
            await WebhookService.push_booking_to_make({
                "patient_email": inserted.get("patient_email"),
                "patient_name": inserted.get("patient_name"),
                "doctor_name": inserted.get("doctor_name"),
                "appointment_time": inserted.get("appointment_time").isoformat() if inserted.get("appointment_time") else None,
            })

        return AppointmentQuery.appointment_booked(
            inserted["patient_name"], inserted["doctor_name"], inserted["id"]
        )
