# routes/chat.py
from fastapi import APIRouter, Depends
from utils.vapi_chatbot import send_message
from database import get_database
from models.chat import ChatRequest  # ⬅️ import from models
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
    
    result = await send_message(user_id, ASSISTANT_ID, request.message, db)
    return result