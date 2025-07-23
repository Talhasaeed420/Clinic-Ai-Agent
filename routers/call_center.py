from fastapi import APIRouter, HTTPException, Query, Request
from models.call_center import (
    ACPurchaseDetails, WarrantyInfo, ServiceVisit, TroubleshootingSteps
)
from motor.motor_asyncio import AsyncIOMotorClient

from database import get_database
import os
import httpx

router = APIRouter()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")

@router.post("/get_ac_purchase_details")
async def get_ac_purchase_details(customer_id: str = Query(...)) -> ACPurchaseDetails:
    db = await get_database_from_callcenter()
    purchase = await db.purchases.find_one({"product_type": "AC", "customer_id": customer_id}, sort=[("purchase_date", -1)])
    if purchase:
        return ACPurchaseDetails(**purchase)
    raise HTTPException(status_code=404, detail="No AC purchase found")

@router.post("/get_warranty_info")
async def get_warranty_info(product_id: str) -> WarrantyInfo:
    db = await get_database_from_callcenter()
    warranty = await db.warranties.find_one({"product_id": product_id})
    if warranty:
        return WarrantyInfo(**warranty)
    raise HTTPException(status_code=404, detail="Warranty info not found")

@router.post("/schedule_service_visit")
async def schedule_service_visit(customer_id: str, product_id: str) -> ServiceVisit:
    db = await get_database_from_callcenter()
    visit_date = "2025-07-20"
    time = "10:00 AM"
    await db.service_visits.insert_one({
        "customer_id": customer_id,
        "product_id": product_id,
        "visit_date": visit_date,
        "time": time
    })
    return ServiceVisit(visit_date=visit_date, time=time)

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
        db = await get_database_from_callcenter()
        await db.calls.insert_one(data["call"])
        return {"status": "call_log_saved"}

    return {"status": "ignored"}

@router.post("/call-center/start-call/")
async def start_callcenter_call(phone_number: str):
    url = "https://api.vapi.ai/v1/conversations"
    headers = {
        "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "phone_number": phone_number,
        "assistant_id": os.getenv("VAPI_ASSISTANT_ID")
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

@router.post("/insert-sample-data")
async def insert_sample_data():
    db = await get_database_from_callcenter()

    await db.purchases.delete_many({"customer_id": {"$in": ["1234", "5678"]}})
    await db.warranties.delete_many({"product_id": {"$in": ["AC-PEL-1234", "AC-SHARP-9876"]}})

    await db.purchases.insert_many([
        {
            "customer_id": "12",
            "name": "Samreen Habib",
            "product_type": "AC",
            "product_model": "PEL-Inverter-12000BTU",
            "product_id": "AC-PEL-1234",
            "purchase_date": "2025-07-01",
            "warranty_status": "Active"
        },
        {
            "customer_id": "56",
            "name": "Ali Raza",
            "product_type": "AC",
            "product_model": "Sharp-CoolPro-1.5Ton",
            "product_id": "AC-SHARP-9876",
            "purchase_date": "2025-06-25",
            "warranty_status": "Active"
        }
    ])

    await db.warranties.insert_many([
        {
            "product_id": "AC-PEL-1234",
            "expiry_date": "2025-12-01",
            "coverage_details": "Covers parts and labor for manufacturing defects"
        },
        {
            "product_id": "AC-SHARP-9876",
            "expiry_date": "2026-06-25",
            "coverage_details": "Full coverage including compressor and gas refill"
        }
    ])

    return {"message": "Sample data inserted"}

async def get_database_from_callcenter():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    return client["appointments_db"]
