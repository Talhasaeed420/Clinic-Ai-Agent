from fastapi import APIRouter, HTTPException, Query, Request
from models.call_center import (
    ACPurchaseDetails, WarrantyInfo, ServiceVisit, TroubleshootingSteps
)
from motor.motor_asyncio import AsyncIOMotorClient
from database import get_database
import os
import httpx
from datetime import datetime, timedelta
from .insertcallcenter import insert_sample_data_to_db 
from constants.constant import ERRORS, SUCCESS  
from constants.workhrs import WORK_START_HOUR, WORK_END_HOUR

router = APIRouter()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")



@router.post("/get_ac_purchase_details")
async def get_ac_purchase_details(customer_id: int = Query(...)) -> ACPurchaseDetails:
    db = await get_database_from_call_center()
    purchase = await db.purchases.find_one(
        {"product_type": "AC", "customer_id": customer_id},
        sort=[("purchase_date", -1)]
    )
    if purchase:
        return ACPurchaseDetails(**purchase)
    raise HTTPException(**ERRORS["NO_AC_PURCHASE"])


@router.post("/get_warranty_info")
async def get_warranty_info(product_id: int) -> WarrantyInfo:
    db = await get_database_from_call_center()
    warranty = await db.warranties.find_one({"product_id": product_id})
    if warranty:
        return WarrantyInfo(**warranty)
    raise HTTPException(**ERRORS["NO_WARRANTY_INFO"])


@router.post("/schedule_service_visit")
async def schedule_service_visit(customer_id: int, product_id: int) -> ServiceVisit:
    db = await get_database_from_call_center()
    now = datetime.now()
    date_cursor = now.replace(minute=0, second=0, microsecond=0)

    while True:
        for hour in range(WORK_START_HOUR, WORK_END_HOUR):
            candidate = date_cursor.replace(hour=hour)

            if candidate <= now:
                continue

            existing = await db.service_visits.find_one({
                "visit_date": candidate.strftime("%Y-%m-%d"),
                "time": candidate.strftime("%I:%M %p")
            })

            if not existing:
                visit_date = candidate.strftime("%Y-%m-%d")
                time = candidate.strftime("%I:%M %p")

                await db.service_visits.insert_one({
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "visit_date": visit_date,
                    "time": time
                })

                return ServiceVisit(visit_date=visit_date, time=time)

        date_cursor = (date_cursor + timedelta(days=1)).replace(hour=WORK_START_HOUR)


@router.post("/get_troubleshooting_steps")
async def get_troubleshooting_steps(issue_description: str) -> TroubleshootingSteps:
    steps = [
        "Check if the unit is properly powered.",
        "Ensure vents are not blocked.",
        "Reset the unit by turning it off and on."
    ]
    return TroubleshootingSteps(steps=steps)


@router.post("/vapi-events")
async def handle_vapi_events(request: Request):
    data = await request.json()
    fn_map = {
        "get_ac_purchase_details": get_ac_purchase_details,
        "get_warranty_info": get_warranty_info,
        "schedule_service_visit": schedule_service_visit,
        "get_troubleshooting_steps": get_troubleshooting_steps,
    }

    if data.get("type") == "tool-calls" and data.get("toolCalls"):
        fn = data["toolCalls"][0]["function"]["name"]
        args = data["toolCalls"][0]["function"]["arguments"]
        if fn in fn_map:
            result = await fn_map[fn](**args)
            return {"result": result.dict()}

    elif data.get("type") == "end_of_call" and data.get("call"):
        db = await get_database_from_call_center()
        await db.calls.insert_one(data["call"])
        return SUCCESS["CALL_LOG_SAVED"]

    return SUCCESS["IGNORED"]


@router.post("/insert-sample-data")
async def insert_sample_data_route():
    db = await get_database_from_call_center()
    result = await insert_sample_data_to_db(db)
    return {"message": result}
async def get_database_from_call_center():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    return client[os.getenv("DB_NAME")]
