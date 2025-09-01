# constants/clinic_status.py

STATUS = {
    "SUCCESS": "success",
    "ERROR": "error",
    "IGNORED": "ignored",
}

ERRORS = {
    "APPOINTMENT_EXISTS": {"status_code": 409, "detail": "Appointment already exists"},
    "APPOINTMENT_CREATE_FAILED": {"status_code": 500, "detail": "Failed to create appointment"},
    "INVALID_APPOINTMENT_ID": {"status_code": 400, "detail": "Invalid appointment ID"},
    "APPOINTMENT_NOT_FOUND": {"status_code": 404, "detail": "Appointment not found"},
    "NO_FIELDS_TO_UPDATE": {"status_code": 400, "detail": "No fields provided for update"},
    "DOCTOR_NOT_FOUND": {"status_code": 404, "detail": "Doctor not found"},
    "DOCTOR_CREATE_FAILED": {"status_code": 500, "detail": "Failed to create doctor"},
    "DOCTOR_UPDATE_FAILED": {"status_code": 500, "detail": "Failed to update doctor"},
    "DOCTOR_DELETE_FAILED": {"status_code": 500, "detail": "Failed to delete doctor"},
    "NO_SPECIALTY_PROVIDED": {"status_code": 400, "detail": "Specialty is required"},
}
