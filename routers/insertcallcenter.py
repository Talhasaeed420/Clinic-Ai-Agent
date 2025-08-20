from motor.motor_asyncio import AsyncIOMotorClient
import os
from constant import ERRORS, SUCCESS


async def insert_sample_data_to_db(db):
    # Delete existing data for these customers and products
    await db.purchases.delete_many({
        "customer_id": {"$in": [12, 56]}
    })
    await db.warranties.delete_many({
        "product_id": {"$in": [45, 44, 99, 98]}
    })

    # Insert new purchase data
    purchase_data = [
        {
            "customer_id": 12,
            "name": "Samreen Habib",
            "product_type": "AC",
            "product_model": "PEL Inverter 12000BTU",
            "product_id": 45,
            "purchase_date": "2025-07-01",
            "warranty_status": "Active"
        },
        {
            "customer_id": 56,
            "name": "Ali Raza",
            "product_type": "AC",
            "product_model": "Sharp CoolPro 1.5Ton",
            "product_id": 44,
            "purchase_date": "2025-06-25",
            "warranty_status": "Active"
        }
    ]
    await db.purchases.insert_many(purchase_data)

    # Insert new warranty data
    warranty_data = [
        {
            "product_id": 45,
            "expiry_date": "2025-12-01",
            "coverage_details": "Covers parts and labor for manufacturing defects"
        },
        {
            "product_id": 44,
            "expiry_date": "2026-06-25",
            "coverage_details": "Full coverage including compressor and gas refill"
        }
    ]
    await db.warranties.insert_many(warranty_data)

    return SUCCESS["SAMPLE_DATA_INSERTED"]
