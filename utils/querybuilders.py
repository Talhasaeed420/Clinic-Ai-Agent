from bson import ObjectId
from datetime import datetime
from fastapi.responses import JSONResponse


class AppointmentQuery:
    """Contains standard queries and JSON response formats."""

    @staticmethod
    def by_id(appointment_id: str):
        """Query to get appointment by its ID"""
        try:
            return {"_id": ObjectId(appointment_id)}
        except Exception:
            return {"_id": None}

    @staticmethod
    def duplicate_check(patient_name: str, doctor_name: str, appointment_time: datetime):
        """Query to check for duplicate appointment"""
        return {
            "$or": [
                {"patient_name": patient_name, "appointment_time": appointment_time},
                {"doctor_name": doctor_name, "appointment_time": appointment_time},
            ]
        }

    # JSON responses
    @staticmethod
    def generic_success(message: str, extra_data: dict = None):
        data = {"message": message}
        if extra_data:
            data.update(extra_data)
        return JSONResponse(content=data, status_code=200)

    @staticmethod
    def error(message: str, status="error"):
        return JSONResponse(content={"status": status, "message": message}, status_code=400)

    @staticmethod
    def appointment_booked(patient_name: str, doctor_name: str, appointment_id: str):
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Appointment booked for {patient_name} with {doctor_name}",
                "appointment_id": appointment_id,
            },
            status_code=200,
        )
