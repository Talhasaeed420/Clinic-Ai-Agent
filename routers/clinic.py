from fastapi import APIRouter, Request, HTTPException
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from dateparser import parse as dateparse
from datetime import datetime, timezone
from clinic_bot_config import insert_clinic_bot_config


# Import constants
from constant import ERRORS, SUCCESS

router = APIRouter()

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
        raise ValueError(f"❌ Cannot parse appointment_time: {raw_time}")

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    dt = dt.replace(second=0, microsecond=0)

    if dt < now:
        raise ValueError(f"❌ Invalid appointment_time: {raw_time}. Past dates are not allowed.")

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
        raise HTTPException(**ERRORS["APPOINTMENT_EXISTS"])

    appointment_data = appointment.dict(by_alias=True, exclude={"id"})
    result = await db.appointments.insert_one(appointment_data)
    inserted = await db.appointments.find_one({"_id": result.inserted_id})

    if inserted:
        inserted["id"] = str(inserted["_id"])
        del inserted["_id"]
        return Appointment(**inserted)

    raise HTTPException(**ERRORS["APPOINTMENT_CREATE_FAILED"])

@router.get("/appointments", response_model=List[Appointment])
async def read_appointments(request: Request):
    db = await get_database(request)
    appointments = await db.appointments.find().to_list(None)
    for appt in appointments:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
    return [Appointment(**appt) for appt in appointments]

@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db = await get_database(request)
    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    except Exception:
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])
    if appt:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
        return Appointment(**appt)
    raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])

@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(**ERRORS["NO_FIELDS_TO_UPDATE"])
    try:
        result = await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    except Exception:
        raise HTTPException(**ERRORS["INVALID_APPOINTMENT_ID"])
    if result.modified_count == 0:
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])
    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    return Appointment(**updated)

# ---------------- WEBHOOK FOR VAPI ---------------- #
@router.post("/webhook")
async def handle_vapi_tool_call(request: Request):
    db = await get_database(request)
    body = await request.json()
    print("Received body:", body)
    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = tool_call_data["arguments"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        print("Function name:", function_name)
        print("Parameters:", parameters)
    except Exception as e:
        print("Error parsing tool call:", e)
        return {"error": "Invalid tool call", "raw": body}

    if function_name == "book_appointment":
        try:
            if "appointment_time" in parameters:
                dt = parse_datetime(parameters["appointment_time"])
                parameters["appointment_time"] = dt
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            existing = await db.appointments.find_one({
                "$or": [
                    {"patient_name": parameters["patient_name"], "appointment_time": parameters["appointment_time"]},
                    {"doctor_name": parameters["doctor_name"], "appointment_time": parameters["appointment_time"]},
                ]
            })
            if existing:
                return {"status": "error", "message": ERRORS["APPOINTMENT_EXISTS"]["detail"]}
            appointment = Appointment(**parameters)
            result = await db.appointments.insert_one(appointment.dict(by_alias=True, exclude={"id"}))
            inserted = await db.appointments.find_one({"_id": result.inserted_id})
            return {
                "status": "success",
                "message": f"✅ Appointment booked for {inserted['patient_name']} with {inserted['doctor_name']} at {inserted['appointment_time']}",
                "appointment_id": str(inserted["_id"]),
            }
        except Exception as e:
            print("DB insert error:", e)
            return {"error": ERRORS["APPOINTMENT_CREATE_FAILED"]["detail"], "raw": parameters}

    elif function_name == "check_availability":
        try:
            if "appointment_time" in parameters:
                dt = parse_datetime(parameters["appointment_time"])
                time = dt
            else:
                return {"status": "error", "message": ERRORS["MISSING_APPOINTMENT_TIME"]["detail"]}
            appointments = await db.appointments.find({"appointment_time": {"$eq": time}}).to_list(None)
            return {"status": "success", "available": len(appointments) == 0}
        except Exception as e:
            print("Availability check error:", e)
            return {"status": "error", "message": str(e)}

    return {"error": "Unknown function", "raw": body}

# ---------------- GETTING ASSISTANT CONFIG FOR VAPI ---------------- #
@router.get("/bot-config")
async def get_assistant_config(request: Request):
    db = await get_database(request)
    config = await db.bot_configs.find_one({}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Assistant configuration not found")
    
    # Log what you're sending to Vapi
    print("Sending config to Vapi:", json.dumps(config, indent=2))
    
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
        return {"message": result}
    except Exception as e:
        return {"error": str(e)}


