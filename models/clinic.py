from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Appointment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    patient_name: str
    doctor_name: str
    appointment_time: datetime
    reason: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True

class AppointmentUpdate(BaseModel):
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    appointment_time: Optional[datetime] = None
    reason: Optional[str] = None
