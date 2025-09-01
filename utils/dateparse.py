from dateparser import parse as dateparse
from datetime import datetime, timezone
import logging

logger = logging.getLogger("utils.dateparse")

def parse_datetime(raw_time: str) -> datetime:
    """
    Parse a natural language datetime string into a UTC-aware datetime object.
    Ensures the result is not in the past.
    """
    dt = dateparse(
        raw_time,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",
            "TO_TIMEZONE": "UTC",
        },
    )

    if not dt:
        logger.error("Cannot parse appointment_time", extra={"raw_time": raw_time})
        raise ValueError(f"Cannot parse appointment_time: {raw_time}")

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    dt = dt.replace(second=0, microsecond=0)

    if dt < now:
        logger.warning("Invalid past appointment_time", extra={"raw_time": raw_time})
        raise ValueError(f"Invalid appointment_time: {raw_time}. Past dates are not allowed.")

    return dt
