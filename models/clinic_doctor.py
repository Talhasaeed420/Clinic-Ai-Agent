from pydantic import BaseModel, Field

class Doctor(BaseModel):
        name: str = Field(..., description="Full name of the doctor")
        specialty: str = Field(..., description="Specialty of the doctor")
        doctor_id: int = Field(..., description="Unique identifier for the doctor")

class SpecialtyRequest(BaseModel):
    specialty: str
