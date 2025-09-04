from fastapi import APIRouter, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.clinic import Appointment, AppointmentUpdate
from database import get_database
from typing import List
from constants.clinic_status import ERRORS
from services.appointment_service import AppointmentService
from services.webhook_service import WebhookService
from utils.querybuilders import AppointmentQuery
import logging

router = APIRouter()
logger = logging.getLogger("appointments")


# ---------------- CRUD ROUTES ---------------- #
@router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: Appointment, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    inserted = await AppointmentService.create_appointment(db, appointment)
    if not inserted:
        logger.error("Appointment creation failed")
        raise HTTPException(**ERRORS["APPOINTMENT_CREATE_FAILED"])
    logger.info("Appointment created", extra={"appointment_id": inserted["id"]})
    return Appointment(**inserted)


@router.get("/appointments", response_model=List[Appointment])
async def read_appointments(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    appointments = await AppointmentService.get_all_appointments(db)
    logger.info("Fetched appointments", extra={"count": len(appointments)})
    return [Appointment(**appt) for appt in appointments]


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def read_appointment(appointment_id: str, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    appt = await AppointmentService.get_appointment_by_id(db, appointment_id)
    if not appt:
        logger.warning("Appointment not found", extra={"appointment_id": appointment_id})
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])
    logger.info("Appointment retrieved", extra={"appointment_id": appointment_id})
    return Appointment(**appt)


@router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_update: AppointmentUpdate, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    updated = await AppointmentService.update_appointment(db, appointment_id, appointment_update)
    if not updated:
        logger.warning("Appointment not found for update", extra={"appointment_id": appointment_id})
        raise HTTPException(**ERRORS["APPOINTMENT_NOT_FOUND"])
    logger.info("Appointment updated", extra={"appointment_id": updated["id"]})
    return Appointment(**updated)


# ---------------- WEBHOOK ROUTES ---------------- #
@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    body = await request.json()
    try:
        response = await WebhookService.handle_end_of_call(db, body)
        return response
    except Exception as e:
        logger.exception("Error processing webhook")
        return AppointmentQuery.error(str(e), status="error")
#------------------Booking-----------------#

@router.post("/bookings")
async def handle_vapi_tool_call(request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    body = await request.json()
    try:
        response = await WebhookService.handle_tool_call(db, body)
        return response
    except Exception as e:
        logger.exception("Error processing tool call")
        return AppointmentQuery.error(str(e), status="error")
