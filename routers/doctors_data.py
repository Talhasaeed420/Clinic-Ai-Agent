from fastapi import APIRouter, Request, HTTPException, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
from database import get_database
from models.clinic_doctor import Doctor
from constants.clinic_status import STATUS, ERRORS

router = APIRouter()
logger = logging.getLogger("appointments")

#---------------- Get doctor by ID ----------------#
@router.get("/get/{doctor_id}")
async def get_doctor(
    doctor_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        doctor = await db["clinic_doctor"].find_one({"doctor_id": doctor_id})
        if not doctor:
            logger.warning("Doctor not found with doctor_id: %s", doctor_id)
            raise HTTPException(**ERRORS["DOCTOR_NOT_FOUND"])

        doctor["_id"] = str(doctor["_id"])
        return {"status": STATUS["SUCCESS"], "doctor": doctor}
    except Exception as e:
        logger.exception("Error fetching doctor: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


#---------------- Add new doctor ----------------#
@router.post("/add")
async def add_doctor(
    doctor: Doctor,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        result = await db["clinic_doctor"].insert_one(doctor.dict())
        return {"status": STATUS["SUCCESS"], "id": str(result.inserted_id)}
    except Exception as e:
        logger.exception("Failed to add doctor: %s", e)
        raise HTTPException(**ERRORS["DOCTOR_CREATE_FAILED"])


#---------------- Delete doctor ----------------#
@router.delete("/delete/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        result = await db["clinic_doctor"].delete_one({"doctor_id": doctor_id})
        if result.deleted_count == 0:
            logger.warning("Doctor not found with doctor_id: %s", doctor_id)
            raise HTTPException(**ERRORS["DOCTOR_NOT_FOUND"])

        logger.info("Deleted doctor with doctor_id: %s", doctor_id)
        return {"status": STATUS["SUCCESS"], "doctor_id": doctor_id}
    except Exception as e:
        logger.exception("Error deleting doctor: %s", e)
        raise HTTPException(**ERRORS["DOCTOR_DELETE_FAILED"])


#---------------- Update doctor ----------------#
@router.put("/update/{doctor_id}")
async def update_doctor(
    doctor_id: int,
    doctor: Doctor,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        result = await db["clinic_doctor"].update_one(
            {"doctor_id": doctor_id},
            {"$set": doctor.dict()}
        )
        if result.modified_count == 0:
            logger.warning("Doctor not found with doctor_id: %s", doctor_id)
            raise HTTPException(**ERRORS["DOCTOR_NOT_FOUND"])

        logger.info("Updated doctor with doctor_id: %s", doctor_id)
        return {"status": STATUS["SUCCESS"], "doctor_id": doctor_id}
    except Exception as e:
        logger.exception("Error updating doctor: %s", e)
        raise HTTPException(**ERRORS["DOCTOR_UPDATE_FAILED"])


#---------------- Get doctors by specialty (for VAPI) ----------------#
@router.get("/specialty")
async def get_doctors_by_specialty(
    specialty: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not specialty:
        raise HTTPException(**ERRORS["NO_SPECIALTY_PROVIDED"])

    cursor = db["clinic_doctor"].find(
        {"specialty": {"$regex": specialty, "$options": "i"}},
        {"name": 1, "_id": 0}
    )
    doctors = await cursor.to_list(length=None)
    return [doc.get("name") for doc in doctors]
