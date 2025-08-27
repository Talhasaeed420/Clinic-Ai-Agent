from fastapi import APIRouter, Request, HTTPException, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from scripts.sync_vapi_assistant import sync_assistant
import json
from dateparser import parse as dateparse
from datetime import datetime, timezone
from constants.constant import ERRORS
import httpx


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
        logger.error("Cannot parse appointment_time: %s", raw_time)
        raise ValueError(f"Cannot parse appointment_time: {raw_time}")

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    dt = dt.replace(second=0, microsecond=0)

    if dt < now:
        logger.warning("Invalid appointment_time: %s. Past dates are not allowed.", raw_time)
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
        logger.info("Duplicate appointment attempt: patient=%s, doctor=%s, time=%s",
                    appointment.patient_name, appointment.doctor_name, appointment.appointment_time)
        raise HTTPException(**ERRORS["APPOINTMENT_EXISTS"])

    appointment_data = appointment.dict(by_alias=True, exclude={"id"})
    result = await db.appointments.insert_one(appointment_data)
    inserted = await db.appointments.find_one({"_id": result.inserted_id})

    if inserted:
        inserted["id"] = str(inserted["_id"])
        del inserted["_id"]
        logger.info("Appointment created: %s", inserted)
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
    logger.info("Fetched %d appointments", len(appointments))
    return [Appointment(**appt) for appt in appointments]


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db = await get_database(request)
    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    except Exception:
        logger.error("Invalid appointment ID: %s", appointment_id)
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])

    if appt:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
        logger.info("Appointment retrieved: %s", appointment_id)
        return Appointment(**appt)

    logger.warning("Appointment not found: %s", appointment_id)
    raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])


@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        logger.warning("No fields to update for appointment_id=%s", appointment_id)
        raise HTTPException(**ERRORS["NO_FIELDS_TO_UPDATE"])

    try:
        result = await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    except Exception:
        logger.error("Invalid appointment ID during update: %s", appointment_id)
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])

    if result.modified_count == 0:
        logger.warning("Appointment not found for update: %s", appointment_id)
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])

    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    logger.info("Appointment updated: %s", updated)
    return Appointment(**updated)


# ---------------- WEBHOOK FOR VAPI ---------------- #
@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    db = await get_database(request)
    body = await request.json()
    logger.info("Received VAPI webhook: %s", body)

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

            await db.calls.insert_one(call_data)
            logger.info("End-of-call report saved. call_id=%s", call_id)
            return JSONResponse(content={"message": "Webhook processed"}, status_code=200)

        except Exception as e:
            logger.exception("Error saving end-of-call report: %s", e)
            return JSONResponse(content={"error": str(e)}, status_code=500)

    logger.info("Webhook ignored (not end-of-call-report)")
    return {"status": "ignored", "message": "Webhook event not handled"}


#----------------Make.com Webhook--------------------------
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/lqq29vebj4f6jlyxht7npxc66w1dgrp6"

ERRORS = {
    "APPOINTMENT_EXISTS": {"detail": "Appointment already exists"},
    "APPOINTMENT_CREATE_FAILED": {"detail": "Failed to create appointment"},
}


# ---------------- BOOKINGS API ---------------- #
@router.post("/bookings")
async def handle_vapi_tool_call(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    body = await request.json()
    logger.info("Received tool call: %s", body)

    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]

        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        logger.info("Tool call function=%s, parameters=%s", function_name, parameters)

    except Exception:
        logger.exception("Error parsing tool call")
        return {"error": "Invalid tool call", "raw": body}

    if function_name == "book_appointment":
        try:
            # normalize appointment_time
            if "appointment_time" in parameters:
                dt = parse_datetime(parameters["appointment_time"])
                dt = dt.replace(second=0, microsecond=0).astimezone(timezone.utc)
                parameters["appointment_time"] = dt
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            logger.info("Normalized appointment_time: %s", parameters["appointment_time"])

            # check duplicates
            existing = await db.appointments.find_one({
                "$or": [
                    {"patient_name": parameters["patient_name"], "appointment_time": parameters["appointment_time"]},
                    {"doctor_name": parameters["doctor_name"], "appointment_time": parameters["appointment_time"]},
                ]
            })
            if existing:
                logger.info("Duplicate appointment detected during booking")
                return {"status": "error", "message": ERRORS["APPOINTMENT_EXISTS"]["detail"]}

            # save appointment
            appointment = Appointment(**parameters)
            result = await db.appointments.insert_one(appointment.dict(by_alias=True, exclude={"id"}))
            inserted = await db.appointments.find_one({"_id": result.inserted_id})
            logger.info("Appointment booked: %s", inserted)

            # 🔥 send appointment details to Make.com webhook
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(MAKE_WEBHOOK_URL, json={
                        "patient_email": inserted.get("patient_email"),
                        "patient_name": inserted.get("patient_name"),
                        "patient_phone": inserted.get("patient_phone"), 
                        "doctor_name": inserted.get("doctor_name"),
                        "appointment_time": inserted.get("appointment_time").isoformat() if inserted.get("appointment_time") else None,
                    })
                logger.info("Appointment pushed to Make.com successfully")
            except Exception as e:
                logger.exception("Failed to send appointment to Make.com")

            return {
                "status": "success",
                "message": f"Appointment booked for {inserted['patient_name']} with {inserted['doctor_name']} at {inserted['appointment_time']}",
                "appointment_id": str(inserted["_id"]),
            }

        except Exception:
            logger.exception("DB insert error")
            return {"error": ERRORS["APPOINTMENT_CREATE_FAILED"]["detail"], "raw": parameters}

    logger.info("Unhandled tool call: %s", function_name)
    return {"status": "ignored", "message": "Webhook event not handled"}