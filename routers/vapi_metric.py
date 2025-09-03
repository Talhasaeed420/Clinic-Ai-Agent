from fastapi import APIRouter, HTTPException
import json 
import requests
import os
from datetime import datetime, timedelta
from models.vapi_metrics import (
    MetricsRequest,
    MetricsResponse,
    RecentCallsResponse,
    CallBreakdownResponse,
    CallSummary,
    CostBreakdownItem,
)
from utils.vapi_cost import metrics_payload

router = APIRouter()

VAPI_TOKEN = os.getenv("VAPI_API_KEY")
VAPI_ANALYTICS_URL = os.getenv("VAPI_ANALYTICS_URL")
VAPI_CALLS_URL = os.getenv("VAPI_CALLS_URL")

headers = {
    "Authorization": f"Bearer {VAPI_TOKEN}",
    "Content-Type": "application/json"
}

# -----------------------------
# Metrics
# -----------------------------
@router.post("/metrics", response_model=MetricsResponse)
def get_metrics(req: MetricsRequest):
    if req.days:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=req.days)
        start = start_date.isoformat() + "Z"
        end = end_date.isoformat() + "Z"
    else:
        start = req.start or "2020-01-01T00:00:00Z"
        end = req.end or datetime.utcnow().isoformat() + "Z"

    payload = metrics_payload(start, end)
    response = requests.post(VAPI_ANALYTICS_URL, headers=headers, json=payload)

    # Parse JSON safely
    try:
        raw_data = response.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid JSON response from analytics API")

    # ✅ VAPI puts actual data inside detail (stringified JSON)
    if isinstance(raw_data, dict) and "detail" in raw_data:
        try:
            data = json.loads(raw_data["detail"])
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse metrics detail JSON")
    else:
        data = raw_data

    result = {
        "total_calls": 0,
        "total_minutes": 0.0,
        "total_cost": 0.0,
        "avg_cost_per_call": 0.0,
    }

    for item in data:
        if item["name"] == "total_calls":
            result["total_calls"] = int(item["result"][0].get("countId", 0))
        elif item["name"] == "total_minutes":
            result["total_minutes"] = float(item["result"][0].get("sumDuration", 0.0))
        elif item["name"] == "total_cost":
            result["total_cost"] = float(item["result"][0].get("sumCost", 0.0))
        elif item["name"] == "avg_cost_per_call":
            result["avg_cost_per_call"] = float(item["result"][0].get("avgCost", 0.0))

    return result


# -----------------------------
# Recent Calls
# -----------------------------
@router.get("/metrics/recent-calls", response_model=RecentCallsResponse)
def get_recent_calls(limit: int = 10):
    params = {"limit": limit}
    response = requests.get(VAPI_CALLS_URL, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    calls = response.json()
    recent_calls = []

    for call in calls:
        call_id = call["id"]
        detail_url = f"{VAPI_CALLS_URL}/{call_id}"
        detail_resp = requests.get(detail_url, headers=headers)
        if detail_resp.status_code != 200:
            continue

        call_detail = detail_resp.json()
        duration_seconds = call_detail.get("duration", 0.0)

        if not duration_seconds:
            started = call_detail.get("startedAt")
            ended = call_detail.get("endedAt") or call_detail.get("updatedAt")
            if started and ended:
                try:
                    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
                    start_dt = datetime.strptime(started, fmt)
                    end_dt = datetime.strptime(ended, fmt)
                    duration_seconds = (end_dt - start_dt).total_seconds()
                except Exception:
                    duration_seconds = 0.0

        duration_minutes = round(duration_seconds / 60, 2)

        recent_calls.append(
            CallSummary(
                id=call_id,
                created_at=call_detail.get("createdAt"),
                duration=duration_minutes,
                cost=call_detail.get("cost", 0.0),
            )
        )

    return {"recent_calls": recent_calls}


# -----------------------------
# Call Breakdown
# -----------------------------
@router.get("/metrics/call/{call_id}/breakdown", response_model=CallBreakdownResponse)
def get_call_breakdown(call_id: str):
    url = f"{VAPI_CALLS_URL}/{call_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    row = response.json()
    breakdown = []
    total_cost = row.get("cost", 0.0)

    if "costBreakdown" in row:
        for k, v in row["costBreakdown"].items():
            if isinstance(v, dict):
                cost = float(v.get("summary", 0.0))
            else:
                try:
                    cost = float(v)
                except:
                    cost = 0.0

            if k in ["transport", "stt", "llm", "tts", "vapi", "chat", "total"]:
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0.0
            else:
                percentage = None

            breakdown.append(
                CostBreakdownItem(
                    category=k,
                    cost=cost,
                    percentage=percentage
                )
            )

    return {"call_id": call_id, "total_cost": total_cost, "breakdown": breakdown}
