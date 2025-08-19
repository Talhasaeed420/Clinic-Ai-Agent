from pydantic import BaseModel
from typing import List

class ACPurchaseDetails(BaseModel):
    customer_id: int
    name: str
    product_type: str
    product_model: str
    product_id: int
    purchase_date: str
    warranty_status: str

class WarrantyInfo(BaseModel):
    product_id: int
    expiry_date: str
    coverage_details: str

class ServiceVisit(BaseModel):
    visit_date: str
    time: str

class TroubleshootingSteps(BaseModel):
    steps: List[str]
