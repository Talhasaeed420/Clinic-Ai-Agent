# routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.admin_service import AdminService
from dependencies.auth import get_current_admin_user

# Import your existing function to get the database connection
from database import get_database  # Adjust this import based on your project structure

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

# ========== CALL LOG ENDPOINTS ==========
@router.get("/call-logs")
async def list_call_logs(
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a list of all call logs (just IDs and timestamps).
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        call_logs = await AdminService.list_call_logs(db, limit)
        return call_logs

    except Exception as e:
        print(f"Error listing call logs: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving call logs")

@router.get("/call-logs/{call_log_id}")
async def get_call_log(
    call_log_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a specific call log with decrypted sensitive data.
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        decrypted_log = await AdminService.get_decrypted_call_log(db, call_log_id)
        
        if decrypted_log is None:
            raise HTTPException(status_code=404, detail="Call log not found")
        
        # Convert ObjectId to a string for JSON response
        decrypted_log["_id"] = str(decrypted_log["_id"])
        return decrypted_log

    except Exception as e:
        print(f"Error decrypting log {call_log_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the log")

# ========== CHAT ENDPOINTS ==========
@router.get("/chats")
async def list_chats(
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a list of all chats (basic info without message content).
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        chats = await AdminService.list_chats(db, limit)
        return chats

    except Exception as e:
        print(f"Error listing chats: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving chats")

@router.get("/chats/{chat_id}")
async def get_chat(
    chat_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a specific chat with decrypted message history.
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        decrypted_chat = await AdminService.get_decrypted_chat(db, chat_id)
        
        if decrypted_chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Convert ObjectId to a string for JSON response
        decrypted_chat["_id"] = str(decrypted_chat["_id"])
        return decrypted_chat

    except Exception as e:
        print(f"Error decrypting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the chat")

# ========== APPOINTMENT ENDPOINTS ==========
@router.get("/appointments")
async def list_appointments(
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a list of all appointments (just basic info without sensitive data).
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        appointments = await AdminService.list_appointments(db, limit)
        return appointments

    except Exception as e:
        print(f"Error listing appointments: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving appointments")

@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: dict = Depends(get_current_admin_user)
):
    """
    Get a specific appointment with decrypted sensitive data.
    REQUIRES ADMIN AUTHENTICATION.
    """
    try:
        decrypted_appointment = await AdminService.get_decrypted_appointment(db, appointment_id)
        
        if decrypted_appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Convert ObjectId to a string for JSON response
        decrypted_appointment["_id"] = str(decrypted_appointment["_id"])
        return decrypted_appointment

    except Exception as e:
        print(f"Error decrypting appointment {appointment_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the appointment")