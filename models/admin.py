from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId
from pydantic import ConfigDict

class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId in Pydantic."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class User(BaseModel):
    """User model for MongoDB."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: Optional[EmailStr] = None
    hashed_password: str
    role: str = "admin"  # Default to admin, but you can add more roles later

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class UserInDB(User):
    """User model with hashed password (for DB storage)."""
    pass

class UserCreate(BaseModel):
    """Input model for creating a user."""
    username: str
    email: Optional[EmailStr] = None
    password: str  # Plaintext, we'll hash it
    role: str = "admin"

class Token(BaseModel):
    """Response model for login (JWT)."""
    access_token: str
    token_type: str = "bearer"