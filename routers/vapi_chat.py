from fastapi import APIRouter, Depends
from utils.vapi_chatbot import send_message
from database import get_database
from models.chat import ChatRequest  # includes optional email
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

router = APIRouter()
ASSISTANT_ID = os.getenv("ASSISTANT_ID")


@router.post("/chat")
async def chat_with_bot(user_id: str, request: ChatRequest, db=Depends(get_database)):
    if not ASSISTANT_ID:
        return {"error": "Assistant ID not configured"}

    email = request.email  # optional from frontend

    # 🔹 If email not provided, fetch from DB using user_id
    if not email:
        try:
            user = await db["users"].find_one({"_id": ObjectId(user_id)}, {"email": 1})
            if user:
                email = user.get("email")
        except Exception as e:
            print("Error fetching email:", e)

    result = await send_message(
        user_id,
        ASSISTANT_ID,
        request.message,
        db,
        email=email
    )
    return result
