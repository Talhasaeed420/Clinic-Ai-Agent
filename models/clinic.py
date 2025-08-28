from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class Appointment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    patient_name: str
    patient_email: EmailStr  # patient's email
    doctor_name: str
    appointment_time: datetime
    reason: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


class AppointmentUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_email: Optional[EmailStr] = None
    doctor_name: Optional[str] = None
    appointment_time: Optional[datetime] = None
    reason: Optional[str] = None
