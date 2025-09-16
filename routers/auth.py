# routers/auth.py - FIXED VERSION
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from dependencies.auth import create_access_token
from database import get_database
from models.admin import Token
from passlib.context import CryptContext
from services.admin_service import AdminService  # Import the actual service

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Login endpoint: Authenticate admin and return JWT.
    """
    # Use the actual AdminService from services
    admin = await AdminService.get_admin_by_username(db, form_data.username)

    if not admin or not AdminService.verify_password(
        form_data.password, admin["hashed_password"]  # Changed from "password" to "hashed_password"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use username instead of email for consistency
    access_token = create_access_token(data={"sub": admin["username"]})
    return {"access_token": access_token, "token_type": "bearer"}