from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ACPurchaseDetails(BaseModel):
    product_model: str
    purchase_date: str
    warranty_status: str
    product_id: str

class WarrantyInfo(BaseModel):
    expiry_date: str
    coverage_details: str

class ServiceVisit(BaseModel):
    visit_date: str
    time: str

class TroubleshootingSteps(BaseModel):
    steps: List[str]

class VapiFunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any]  

class ToolCall(BaseModel):
    id: str
    type: str
    function: VapiFunctionCall

class VapiEvent(BaseModel):
    type: str
    call: Optional[Dict[str, Any]] = None
    toolCalls: Optional[List[ToolCall]] = None
