from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    email: Optional[EmailStr] = None   # ✅ optional now
