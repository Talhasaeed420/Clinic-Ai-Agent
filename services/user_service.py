from motor.motor_asyncio import AsyncIOMotorDatabase
from models.admin import UserInDB, UserCreate
from passlib.context import CryptContext
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AdminService:
    @staticmethod
    async def get_admin_by_username(db: AsyncIOMotorDatabase, username: str) -> Optional[UserInDB]:
        """Fetch an admin by username from the admins collection."""
        admin_dict = await db.admins.find_one({"username": username})
        if admin_dict:
            return UserInDB(**admin_dict)
        return None

    @staticmethod
    async def create_admin(db: AsyncIOMotorDatabase, admin: UserCreate) -> UserInDB:
        """Create a new admin with hashed password."""
        hashed_password = pwd_context.hash(admin.password)
        admin_dict = admin.dict(exclude={"password"})
        admin_dict["password"] = hashed_password  # keep consistent naming
        result = await db.admins.insert_one(admin_dict)
        created_admin = await db.admins.find_one({"_id": result.inserted_id})
        return UserInDB(**created_admin)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against the hashed version."""
        return pwd_context.verify(plain_password, hashed_password)
