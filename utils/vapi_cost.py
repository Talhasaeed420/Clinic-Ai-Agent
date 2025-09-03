from datetime import datetime

def metrics_payload(start: str, end: str):
    """
    Returns the payload for VAPI metrics API.
    """
    return {
        "queries": [
            {
                "table": "call",
                "name": "total_calls",
                "timeRange": {"start": start, "end": end, "timezone": "UTC"},
                "operations": [{"operation": "count", "column": "id"}],
            },
            {
                "table": "call",
                "name": "total_minutes",
                "timeRange": {"start": start, "end": end, "timezone": "UTC"},
                "operations": [{"operation": "sum", "column": "duration"}],
            },
            {
                "table": "call",
                "name": "total_cost",
                "timeRange": {"start": start, "end": end, "timezone": "UTC"},
                "operations": [{"operation": "sum", "column": "cost"}],
            },
            {
                "table": "call",
                "name": "avg_cost_per_call",
                "timeRange": {"start": start, "end": end, "timezone": "UTC"},
                "operations": [{"operation": "avg", "column": "cost"}],
            },
        ]
    }
