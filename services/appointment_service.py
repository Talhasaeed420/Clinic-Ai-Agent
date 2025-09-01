from motor.motor_asyncio import AsyncIOMotorDatabase
from models.clinic import Appointment
from utils.querybuilders import AppointmentQuery
from datetime import datetime


class AppointmentService:
    """All database logic related to appointments."""

    @staticmethod
    async def find_duplicate(db: AsyncIOMotorDatabase, patient_name: str, doctor_name: str, appointment_time: datetime):
        """Check if an appointment already exists for a patient or doctor at the same time."""
        query = AppointmentQuery.duplicate_check(patient_name, doctor_name, appointment_time)
        return await db.appointments.find_one(query)

    @staticmethod
    async def create(db: AsyncIOMotorDatabase, appointment: Appointment):
        """Create a new appointment in the database."""
        # Check for duplicate
        existing = await AppointmentService.find_duplicate(
            db, appointment.patient_name, appointment.doctor_name, appointment.appointment_time
        )
        if existing:
            return None

        data = appointment.dict(by_alias=True, exclude={"id"})
        result = await db.appointments.insert_one(data)
        inserted = await db.appointments.find_one({"_id": result.inserted_id})
        if inserted:
            inserted["id"] = str(inserted["_id"])
            del inserted["_id"]
        return inserted

    @staticmethod
    async def get_all(db: AsyncIOMotorDatabase):
        """Get all appointments from the database."""
        appointments = await db.appointments.find().to_list(None)
        for appt in appointments:
            appt["id"] = str(appt["_id"])
            del appt["_id"]
        return appointments

    @staticmethod
    async def get_by_id(db: AsyncIOMotorDatabase, appointment_id: str):
        """Get a single appointment by its ID."""
        appt = await db.appointments.find_one(AppointmentQuery.by_id(appointment_id))
        if appt:
            appt["id"] = str(appt["_id"])
            del appt["_id"]
        return appt

    @staticmethod
    async def update(db: AsyncIOMotorDatabase, appointment_id: str, update_data: dict):
        """Update an existing appointment."""
        if not update_data:
            return None

        result = await db.appointments.update_one(
            AppointmentQuery.by_id(appointment_id),
            {"$set": update_data}
        )
        if result.modified_count == 0:
            return None

        updated = await db.appointments.find_one(AppointmentQuery.by_id(appointment_id))
        if updated:
            updated["id"] = str(updated["_id"])
            del updated["_id"]
        return updated
