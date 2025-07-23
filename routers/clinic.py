from fastapi import APIRouter, Request, HTTPException
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from bson import ObjectId
import json

router = APIRouter()

@router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    db = await get_database(request)
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
        appt["_id"] = str(appt["_id"])
    return [Appointment(**appt) for appt in appointments]

@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db = await get_database(request)
    appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    if appt:
        appt["id"] = str(appt["_id"])
        return Appointment(**appt)
    raise HTTPException(status_code=404, detail="Appointment not found")

@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.appointments.update_one({"_id": ObjectId(appointment_id)}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    updated["id"] = str(updated["_id"])
    return Appointment(**updated)

@router.post("/vapi/tool")
async def handle_vapi_tool_call(request: Request):
    db = await get_database(request)
    body = await request.json()
    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        parameters = json.loads(tool_call_data["arguments"])
    except Exception:
        return {"error": "Invalid tool call", "raw": body}

    if function_name == "book_appointment":
        appointment = Appointment(**parameters)
        result = await db.appointments.insert_one(appointment.dict(by_alias=True, exclude={"id"}))
        inserted = await db.appointments.find_one({"_id": result.inserted_id})
        return {
            "status": "success",
            "message": f"Appointment booked for {inserted['patient_name']} at {inserted['appointment_time']}",
            "appointment_id": str(inserted["_id"])
        }

    elif function_name == "check_availability":
        time = parameters.get("appointment_time")
        appointments = await db.appointments.find({"appointment_time": {"$eq": time}}).to_list(None)
        return {
            "status": "success",
            "available": len(appointments) == 0
        }

    return {"error": "Unknown function", "raw": body}
