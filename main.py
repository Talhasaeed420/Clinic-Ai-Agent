from fastapi import FastAPI, HTTPException, Request
from models import Appointment, AppointmentUpdate
from database import lifespan, get_database
from pydantic import BaseModel
from typing import List
from bson import ObjectId
import httpx
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(lifespan=lifespan)

# --- 1. For Vapi tool calls
class AppointmentToolCall(BaseModel):
    function: str
    parameters: dict

# --- 2. Create Appointment API
@app.post("/api/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    print("[LOG] Received API request to create appointment")
    db = await get_database(request)
    appointment_data = appointment.dict(by_alias=True, exclude={"id"})
    result = await db.appointments.insert_one(appointment_data)
    print("[LOG] Inserted ID:", result.inserted_id)

    inserted = await db.appointments.find_one({"_id": result.inserted_id})
    if inserted:
        inserted["id"] = str(inserted["_id"])
        del inserted["_id"]
        print("[LOG] Inserted Document:", inserted)
        return Appointment(**inserted)
    raise HTTPException(status_code=500, detail="Failed to create appointment")

# --- 3. Get All Appointments
@app.get("/api/appointments", response_model=List[Appointment])
async def read_appointments(request: Request):
    print("[LOG] Reading all appointments")
    db = await get_database(request)
    appointments = await db.appointments.find().to_list(None)
    for appointment in appointments:
        appointment["_id"] = str(appointment["_id"])  
    print("[LOG] Total Appointments Found:", len(appointments))
    return [Appointment(**appointment) for appointment in appointments]

# --- 4. Get One Appointment by ID
@app.get("/api/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    print(f"[LOG] Reading appointment with ID: {appointment_id}")
    db = await get_database(request)
    appointment = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    if appointment:
        appointment["id"] = str(appointment["_id"])
        return Appointment(**appointment)
    raise HTTPException(status_code=404, detail="Appointment not found")

# --- 5. Update Appointment
@app.patch("/api/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    print(f"[LOG] Updating appointment with ID: {appointment_id}")
    db = await get_database(request)
    update_data = {k: v for k, v in appointment_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")

    updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    updated["id"] = str(updated["_id"])
    print("[LOG] Updated Document:", updated)
    return Appointment(**updated)

# --- 6. Vapi Voice Bot: Tool Call Handler
@app.post("/api/vapi/tool")
async def handle_vapi_tool_call(request: Request):
    body = await request.json()
    print("[DEBUG] Raw VAPI tool call:", body)

    db = await get_database(request)

    try:
        tool_call_data = body["message"]["toolCalls"][0]["function"]
        function_name = tool_call_data["name"]
        arguments_str = tool_call_data["arguments"]

        # Parse arguments if they are a JSON string
        if isinstance(arguments_str, str):
            parameters = json.loads(arguments_str)
        else:
            parameters = arguments_str

        print("[DEBUG] Parsed Function:", function_name)
        print("[DEBUG] Parsed Parameters:", parameters)
    except Exception as e:
        print("[ERROR] Could not parse tool call:", e)
        return {"error": "Invalid tool call structure", "raw": body}

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

# --- 7. Start Call API (optional)
@app.post("/start-call/")
async def start_call(phone_number: str):
    print(f"[LOG] Starting call to: {phone_number}")
    url = "https://api.vapi.ai/v1/conversations"
    headers = {
        "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "phone_number": phone_number,
        "assistant_id": os.getenv("ASSISTANT_ID")
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print("[ERROR] VAPI call failed:", response.text)
            raise HTTPException(status_code=response.status_code, detail=response.text)
        print("[LOG] VAPI call started successfully")
        return response.json()
