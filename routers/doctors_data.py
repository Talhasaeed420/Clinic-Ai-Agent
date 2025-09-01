
from fastapi import APIRouter, Request, HTTPException, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
from database import get_database
from typing import List
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from scripts.sync_vapi_assistant import sync_assistant
from models.clinic_doctor import Doctor
import json
from datetime import datetime, timezone
from constants.constant import ERRORS

router = APIRouter()
logger = logging.getLogger("appointments")



#---------------For getting doctor---------
@router.get("/get/{doctor_id}")
async def get_doctor(
    doctor_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        doctor = await db["clinic_doctor"].find_one({"doctor_id": doctor_id})
        
        if not doctor:
            logger.warning("Doctor not found with doctor_id: %s", doctor_id)
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        # Convert ObjectId to str
        doctor["_id"] = str(doctor["_id"])
        
        return {"status": "success", "doctor": doctor}
    except Exception as e:
        logger.exception("Error fetching doctor: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


#---------------------For inserting clinic doctors---------------

@router.post("/add")
async def add_doctor(
    doctor: Doctor,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        result = await db["clinic_doctor"].insert_one(doctor.dict())
        return{"status": "success", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#------------------For deleting clinic doctors---------------

@router.delete("/delete/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        # Delete by doctor_id (custom field), not by Mongo _id
        result = await db["clinic_doctor"].delete_one({"doctor_id": doctor_id})
        
        if result.deleted_count == 0:
            logger.warning("Doctor not found with doctor_id: %s", doctor_id)
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        logger.info("Deleted doctor with doctor_id: %s", doctor_id)
        return {"status": "success", "doctor_id": doctor_id}
    except Exception as e:
        logger.exception("Error deleting doctor: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


#------------------For updating clinic doctors---------------
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
            raise HTTPException(status_code=404, detail="Doctor not found")
        logger.info("Updated doctor with doctor_id: %s", doctor_id)
        return {"status": "success", "doctor_id": doctor_id}
    except Exception as e:
        logger.exception("Error updating doctor: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

#------------------For getting doctor by speciality (For vapi)-----------


@router.get("/specialty")
async def get_doctors_by_specialty(
    specialty: str,  # reads from query param
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not specialty:
        raise HTTPException(status_code=400, detail="Specialty is required")

    cursor = db["clinic_doctor"].find(
        {"specialty": {"$regex": specialty, "$options": "i"}},
        {"name": 1, "_id": 0}  # only doctor names
    )
    doctors = await cursor.to_list(length=None)

    return [doc.get("name") for doc in doctors]
