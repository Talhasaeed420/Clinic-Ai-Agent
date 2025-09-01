from fastapi import APIRouter, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from datetime import datetime, timezone
from constants.clinic_status import STATUS, ERRORS
from utils.dateparse import parse_datetime
from services.appointment_service import AppointmentService
from services.webhook_service import WebhookService
from utils.querybuilders import AppointmentQuery
import logging
import json

router = APIRouter()
logger = logging.getLogger("appointments")


# ---------------- CRUD ROUTES ---------------- #
@router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    existing = await AppointmentService.find_duplicate(
        db, appointment.patient_name, appointment.doctor_name, appointment.appointment_time
    )
    if existing:
        logger.info("Duplicate appointment attempt", extra={"appointment": appointment.dict()})
        raise HTTPException(**ERRORS["APPOINTMENT_EXISTS"])

    inserted = await AppointmentService.create(db, appointment)
    if not inserted:
        logger.error("Appointment creation failed")
        raise HTTPException(**ERRORS["APPOINTMENT_CREATE_FAILED"])

    logger.info("Appointment created", extra={"appointment_id": inserted["id"]})
    return Appointment(**inserted)


@router.get("/appointments", response_model=List[Appointment])
async def read_appointments(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    appointments = await AppointmentService.get_all(db)
    logger.info("Fetched appointments", extra={"count": len(appointments)})
    return [Appointment(**appt) for appt in appointments]


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    appt = await AppointmentService.get_by_id(db, appointment_id)
    if not appt:
        logger.warning("Appointment not found", extra={"appointment_id": appointment_id})
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])
    logger.info("Appointment retrieved", extra={"appointment_id": appointment_id})
    return Appointment(**appt)


@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        logger.warning("No fields to update", extra={"appointment_id": appointment_id})
        raise HTTPException(**ERRORS["NO_FIELDS_TO_UPDATE"])

    updated = await AppointmentService.update(db, appointment_id, update_data)
    if not updated:
        logger.warning("Appointment not found for update", extra={"appointment_id": appointment_id})
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])

    logger.info("Appointment updated", extra={"appointment_id": updated["id"]})
    return Appointment(**updated)


# ---------------- WEBHOOK FOR VAPI ---------------- #
@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    body = await request.json()
    logger.info("Received VAPI webhook", extra={"body": body})

    message = body.get("message", {})
    if message.get("type") != "end-of-call-report":
        logger.info("Webhook ignored (not end-of-call-report)")
        return AppointmentQuery.generic_success("Webhook event not handled", {"status": STATUS["IGNORED"]})

    try:
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
        logger.info("End-of-call report saved", extra={"call_id": call_id})

        if corrected_number:
            try:
                await WebhookService.push_sms_to_make(corrected_number)
                logger.info("Caller phone pushed to Make.com", extra={"phone": corrected_number})
            except Exception:
                logger.exception("Failed to push phone to Make.com")

        return AppointmentQuery.generic_success("Webhook processed")

    except Exception as e:
        logger.exception("Error saving end-of-call report")
        return AppointmentQuery.error(str(e), status="error")


# ---------------- BOOKINGS API ---------------- #
@router.post("/bookings")
async def handle_vapi_tool_call(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    body = await request.json()
    logger.info("Received tool call", extra={"body": body})

    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]

        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        logger.info("Tool call parsed", extra={"function": function_name, "parameters": parameters})

    except Exception:
        logger.exception("Error parsing tool call")
        return AppointmentQuery.error("Invalid tool call received.", status="error")

    if function_name == "book_appointment":
        try:
            if "appointment_time" in parameters:
                parameters["appointment_time"] = parse_datetime(parameters["appointment_time"])
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            existing = await AppointmentService.find_duplicate(
                db, parameters["patient_name"], parameters["doctor_name"], parameters["appointment_time"]
            )

            if existing:
                logger.info("Duplicate appointment detected", extra={"parameters": parameters})
                return AppointmentQuery.error(ERRORS["APPOINTMENT_EXISTS"]["detail"], status="error")

            appointment = Appointment(**parameters)
            inserted = await AppointmentService.create(db, appointment)
            logger.info("Appointment booked", extra={"appointment_id": inserted["id"]})

            if inserted:
                await WebhookService.push_booking_to_make({
                    "patient_email": inserted.get("patient_email"),
                    "patient_name": inserted.get("patient_name"),
                    "doctor_name": inserted.get("doctor_name"),
                    "appointment_time": inserted.get("appointment_time").isoformat()
                    if inserted.get("appointment_time") else None,
                })

            return AppointmentQuery.appointment_booked(
                inserted["patient_name"], inserted["doctor_name"], inserted["id"]
            )

        except Exception:
            logger.exception("DB insert error")
            return AppointmentQuery.error(ERRORS["APPOINTMENT_CREATE_FAILED"]["detail"], status="error")

    logger.info("Unhandled tool call", extra={"function": function_name})
    return AppointmentQuery.error("This webhook event was not handled.", status="error")
