from fastapi import status


ERRORS = {
    # ------- Call Center -------
    "NO_AC_PURCHASE": {
        "status_code": status.HTTP_404_NOT_FOUND,
        "detail": "No AC purchase found"
    },
    "NO_WARRANTY_INFO": {
        "status_code": status.HTTP_404_NOT_FOUND,
        "detail": "Warranty info not found"
    },
    "VAPI_REQUEST_FAILED": {
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "VAPI request failed"
    },

    # ------- Clinic -------
    "APPOINTMENT_EXISTS": {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "❌ Appointment already exists for this time (same patient or same doctor). Please choose another time."
    },
    "APPOINTMENT_CREATE_FAILED": {
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "Failed to create appointment"
    },
    "INVALID_APPOINTMENT_ID": {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "Invalid appointment ID format"
    },
    "APPOINTMENT_NOT_FOUND": {
        "status_code": status.HTTP_404_NOT_FOUND,
        "detail": "Appointment not found"
    },
    "NO_FIELDS_TO_UPDATE": {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "No fields to update"
    },
    "MISSING_APPOINTMENT_TIME": {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "Missing appointment_time"
    },
    "CANNOT_PARSE_APPOINTMENT_TIME": {   # ✅ NEW
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "❌ Cannot parse appointment_time"
    },
    "INVALID_PAST_APPOINTMENT_TIME": {   # ✅ NEW
        "status_code": status.HTTP_400_BAD_REQUEST,
        "detail": "❌ Invalid appointment_time. Past dates are not allowed."
    },
}

# =========================
# SUCCESS RESPONSES
# =========================
SUCCESS = {
    "APPOINTMENT_BOOKED": "✅ Appointment booked successfully",
    "APPOINTMENT_UPDATED": "✅ Appointment updated successfully",
    "CALL_LOG_SAVED": {"status": "call_log_saved"},
    "SAMPLE_DATA_INSERTED": {"message": "Sample data inserted"},
    "IGNORED": {"status": "ignored"},
}
