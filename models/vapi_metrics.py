from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# -----------------------------
# Request
# -----------------------------
class MetricsRequest(BaseModel):
    start: Optional[str] = None  # ISO date string
    end: Optional[str] = None
    days: Optional[int] = None   # e.g., last 7 days


# -----------------------------
# Responses
# -----------------------------
class MetricsResponse(BaseModel):
    total_calls: int
    total_minutes: float
    total_cost: float
    avg_cost_per_call: float


class CallSummary(BaseModel):
    id: str
    created_at: datetime
    duration: float
    cost: float


class RecentCallsResponse(BaseModel):
    recent_calls: List[CallSummary]


class CostBreakdownItem(BaseModel):
    category: str
    cost: float
    percentage: Optional[float] = None


class CallBreakdownResponse(BaseModel):
    call_id: str
    total_cost: float
    breakdown: List[CostBreakdownItem]
