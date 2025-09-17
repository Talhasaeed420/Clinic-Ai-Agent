from fastapi import APIRouter, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database
from pydantic import BaseModel
import bcrypt

router = APIRouter()

# ---------------- Models ---------------- #
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str


# ---------------- Register ---------------- #
@router.post("/users/register")
async def register_user(user: UserRegister, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    users = db["users"]

    # check if user already exists
    existing = await users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())
    result = await users.insert_one({
        "email": user.email,
        "password": hashed_pw.decode("utf-8")
    })

    return {"status": "success", "user_id": str(result.inserted_id)}


# ---------------- Login ---------------- #
@router.post("/users/login")
async def login_user(user: UserLogin, request: Request):
    db: AsyncIOMotorDatabase = await get_database(request)
    users = db["users"]

    db_user = await users.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not bcrypt.checkpw(user.password.encode("utf-8"), db_user["password"].encode("utf-8")):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {"status": "success", "user_id": str(db_user["_id"])}
