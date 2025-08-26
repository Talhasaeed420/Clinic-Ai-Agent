from fastapi import APIRouter, Request, HTTPException
import logging
logger = logging.getLogger("appointments")
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from bson import ObjectId
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from dateparser import parse as dateparse
from datetime import datetime, timezone
from models.mainvapidata import BotConfig, VapiCallReport
from models.mainvapidata import CallAnalysis, CallArtifact, CostBreakdown, PerformanceMetrics, CallInfo, AssistantInfo

from constants.constant import ERRORS, SUCCESS

router = APIRouter()
logger = logging.getLogger("appointments")

# ---------------- HELPERS ---------------- #
def parse_datetime(raw_time: str) -> datetime:
    dt = dateparse(
        raw_time,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",
            "TO_TIMEZONE": "UTC",
        },
    )

    if not dt:
        logger.error(f"Cannot parse appointment_time: {raw_time}")
        raise ValueError(f"Cannot parse appointment_time: {raw_time}")

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    dt = dt.replace(second=0, microsecond=0)

    if dt < now:
        logger.warning(f"Invalid appointment_time: {raw_time}. Past dates are not allowed.")
        raise ValueError(f"Invalid appointment_time: {raw_time}. Past dates are not allowed.")

    return dt

# ---------------- CRUD ROUTES ---------------- #
@router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    db = await get_database(request)
    existing = await db.appointments.find_one({
        "$or": [
            {"patient_name": appointment.patient_name, "appointment_time": appointment.appointment_time},
            {"doctor_name": appointment.doctor_name, "appointment_time": appointment.appointment_time},
        ]
    })
    if existing:
        logger.info(f"Duplicate appointment attempt for patient={appointment.patient_name}, doctor={appointment.doctor_name}, time={appointment.appointment_time}")
        raise HTTPException(**ERRORS["APPOINTMENT_EXISTS"])

    appointment_data = appointment.dict(by_alias=True, exclude={"id"})
    result = await db.appointments.insert_one(appointment_data)
    inserted = await db.appointments.find_one({"_id": result.inserted_id})

    if inserted:
        inserted["id"] = str(inserted["_id"])
        del inserted["_id"]
        logger.info(f"Appointment created: {inserted}")
        return Appointment(**inserted)

    logger.error("Appointment creation failed")
    raise HTTPException(**ERRORS["APPOINTMENT_CREATE_FAILED"])


@router.get("/appointments", response_model=List[Appointment])
async def read_appointments(request: Request):
    db = await get_database(request)
    appointments = await db.appointments.find().to_list(None)
    for appt in appointments:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
    logger.info(f"Fetched {len(appointments)} appointments")
    return [Appointment(**appt) for appt in appointments]


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db = await get_database(request)
    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    except Exception:
        logger.error(f"Invalid appointment ID: {appointment_id}")
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])

    if appt:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
        logger.info(f"Appointment retrieved: {appointment_id}")
        return Appointment(**appt)

    logger.warning(f"Appointment not found: {appointment_id}")
    raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])


@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        logger.warning(f"No fields to update for appointment_id={appointment_id}")
        raise HTTPException(**ERRORS["NO_FIELDS_TO_UPDATE"])

    try:
        result = await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    except Exception:
        logger.error(f"Invalid appointment ID during update: {appointment_id}")
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])

    if result.modified_count == 0:
        logger.warning(f"Appointment not found for update: {appointment_id}")
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])

    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    logger.info(f"Appointment updated: {updated}")
    return Appointment(**updated)


# ---------------- WEBHOOK FOR VAPI ---------------- #
@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    db = await get_database(request)
    body = await request.json()
    logger.info(f"Received VAPI webhook: {body}")

    message = body.get("message", {})

    if message.get("type") == "end-of-call-report":
        try:
            call_id = body.get("call", {}).get("id")

            await db.callslog.insert_one({
                "body": body,
                "receivedAt": datetime.utcnow()
            })

            if call_id:
                await db.calls.delete_one({"call.id": call_id})

            call_data = {
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
                "analysis": message.get("analysis", {}),
                "artifact": message.get("artifact", {}),
                "performanceMetrics": body.get("performanceMetrics", {}),
                "call": body.get("call", {}),
                "assistant": body.get("assistant", {}),
                "updatedAt": datetime.utcnow()
            }

            result = await db.calls.insert_one(call_data)
            logger.info(f"End-of-call report saved. call_id={call_id}")
            return JSONResponse(content={"message": "Webhook processed"}, status_code=200)

        except Exception as e:
            logger.exception(f"Error saving end-of-call report: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

    logger.info("Webhook ignored (not end-of-call-report)")
    return {"status": "ignored", "message": "Webhook event not handled"}

#----------------Bookings APi------------------
@router.post("/bookings")
async def handle_vapi_tool_call(request: Request):
    db = await get_database(request)
    body = await request.json()
    logger.info(f"Received tool call: {body}")

    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]

        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        logger.info(f"Tool call function={function_name}, parameters={parameters}")

    except Exception as e:
        logger.exception("Error parsing tool call")
        return {"error": "Invalid tool call", "raw": body}

    if function_name == "book_appointment":
        try:
            # Parse and normalize appointment_time
            if "appointment_time" in parameters:
                dt = parse_datetime(parameters["appointment_time"])
                if not dt:
                    return {"status": "error", "message": "Invalid date format"}
                dt = dt.replace(second=0, microsecond=0).astimezone(timezone.utc)
                parameters["appointment_time"] = dt
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            logger.info(f"Normalized appointment_time: {parameters['appointment_time']}")

            # Check availability (doctor OR patient at the same time)
            existing = await db.appointments.find_one({
                "$or": [
                    {"patient_name": parameters["patient_name"], "appointment_time": parameters["appointment_time"]},
                    {"doctor_name": parameters["doctor_name"], "appointment_time": parameters["appointment_time"]},
                ]
            })

            if existing:
                logger.info("Duplicate appointment detected during booking")
                return {"status": "error", "message": ERRORS["APPOINTMENT_EXISTS"]["detail"]}

            # Insert appointment
            appointment = Appointment(**parameters)
            result = await db.appointments.insert_one(appointment.dict(by_alias=True, exclude={"id"}))
            inserted = await db.appointments.find_one({"_id": result.inserted_id})

            logger.info(f"Appointment booked: {inserted}")
            return {
                "status": "success",
                "message": f"Appointment booked for {inserted['patient_name']} with {inserted['doctor_name']} at {inserted['appointment_time']}",
                "appointment_id": str(inserted["_id"]),
            }

        except Exception as e:
            logger.exception("DB insert error")
            return {"error": ERRORS["APPOINTMENT_CREATE_FAILED"]["detail"], "raw": parameters}

    logger.info("Unhandled tool call")
    return {"status": "ignored", "message": "Webhook event not handled"}





# ---------------- GETTING ASSISTANT CONFIG FOR VAPI ---------------- #
@router.get("/bot-config")
async def get_assistant_config(request: Request):
    db = await get_database(request)
    config = await db.bot_configs.find_one({}, {"_id": 0})
    if not config:
        logger.warning("Assistant configuration not found")
        raise HTTPException(status_code=404, detail="Assistant configuration not found")
    
    logger.info(f"Sending config to Vapi: {json.dumps(config, indent=2)}")
    return config


# ---------------- INSERT CLINIC BOT CONFIG ---------------- #
async def get_database_from_clinic():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    return client[os.getenv("DB_NAME")]

@router.post("/insert-clinic-bot-config")
async def insert_clinic_bot_config_route():
    db = await get_database_from_clinic()
    try:
        result = await insert_clinic_bot_config(db)
        logger.info(f"Inserted clinic bot config: {result}")
        return {"message": result}
    except Exception as e:
        logger.exception(f"Error inserting clinic bot config: {e}")
        return {"error": str(e)}
