from fastapi import APIRouter, Request, HTTPException
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from bson import ObjectId
import json
from dateparser import parse as dateparse
from datetime import datetime, timedelta, timezone

router = APIRouter()

# ---------------- HELPERS ---------------- #

def parse_datetime(raw_time: str) -> datetime:
    """Parse natural language into UTC datetime (minute precision)."""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    text = raw_time.lower().strip()

    # --- Manual handling for relative dates ---
    if "tomorrow" in text:
        parsed = dateparse(text.replace("tomorrow", ""), settings={"TIMEZONE": "UTC"})
        if parsed:
            return (now + timedelta(days=1)).replace(
                hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0
            )
        return now + timedelta(days=1)

    if "today" in text:
        parsed = dateparse(text.replace("today", ""), settings={"TIMEZONE": "UTC"})
        if parsed:
            return now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
        return now

    # --- Fallback for explicit dates (e.g. "19 August 2025 4pm") ---
    dt = dateparse(raw_time, settings={"TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True})
    if dt:
        return dt.replace(second=0, microsecond=0)

    raise ValueError(f"Cannot parse appointment_time: {raw_time}")


# ---------------- CRUD ROUTES ---------------- #

@router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    db = await get_database(request)

    # Prevent duplicate: same patient + same time OR same doctor + same time
    existing = await db.appointments.find_one({
        "$or": [
            {"patient_name": appointment.patient_name, "appointment_time": appointment.appointment_time},
            {"doctor_name": appointment.doctor_name, "appointment_time": appointment.appointment_time}
        ]
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="❌ Appointment already exists for this time (same patient or same doctor). Please choose another time."
        )

    appointment_data = appointment.dict(by_alias=True, exclude={"id"})
    result = await db.appointments.insert_one(appointment_data)
    inserted = await db.appointments.find_one({"_id": result.inserted_id})

    if inserted:
        inserted["id"] = str(inserted["_id"])
        del inserted["_id"]
        return Appointment(**inserted)

    raise HTTPException(status_code=500, detail="Failed to create appointment")


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
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    if appt:
        appt["id"] = str(appt["_id"])
        del appt["_id"]
        return Appointment(**appt)

    raise HTTPException(status_code=404, detail="Appointment not found")


@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")

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

    # --- BOOK APPOINTMENT ---
    if function_name == "book_appointment":
        try:
            if "appointment_time" in parameters:
                raw_time = parameters["appointment_time"]
                dt = parse_datetime(raw_time)
                parameters["appointment_time"] = dt
            else:
                parameters["appointment_time"] = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            # --- CHECK for duplicate ---
            existing = await db.appointments.find_one({
                "$or": [
                    {"patient_name": parameters["patient_name"], "appointment_time": parameters["appointment_time"]},
                    {"doctor_name": parameters["doctor_name"], "appointment_time": parameters["appointment_time"]}
                ]
            })

            if existing:
                return {
                    "status": "error",
                    "message": f"❌ Appointment conflict: either patient {parameters['patient_name']} "
                               f"or doctor {parameters['doctor_name']} already has an appointment at {parameters['appointment_time']}. "
                               f"Please choose another time."
                }

            # Insert new appointment
            appointment = Appointment(**parameters)
            result = await db.appointments.insert_one(
                appointment.dict(by_alias=True, exclude={"id"})
            )
            inserted = await db.appointments.find_one({"_id": result.inserted_id})

            return {
                "status": "success",
                "message": f"✅ Appointment booked for {inserted['patient_name']} "
                           f"with {inserted['doctor_name']} at {inserted['appointment_time']}",
                "appointment_id": str(inserted["_id"])
            }

        except Exception as e:
            print("DB insert error:", e)
            return {"error": "Failed to insert appointment", "raw": parameters}

    # --- CHECK AVAILABILITY ---
    elif function_name == "check_availability":
        try:
            if "appointment_time" in parameters:
                raw_time = parameters["appointment_time"]
                dt = parse_datetime(raw_time)
                time = dt
            else:
                return {"status": "error", "message": "Missing appointment_time"}

            appointments = await db.appointments.find(
                {"appointment_time": {"$eq": time}}
            ).to_list(None)

            return {
                "status": "success",
                "available": len(appointments) == 0
            }

        except Exception as e:
            print("Availability check error:", e)
            return {"status": "error", "message": str(e)}

    # --- UNKNOWN FUNCTION ---
    return {"error": "Unknown function", "raw": body}
