# utils/vapi_chatbot.py
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import httpx  # async http client (non-blocking)

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
BASE_URL = "https://api.vapi.ai/chat"


def _extract_reply_and_tool(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Robustly extract a displayable assistant reply and/or a tool call
    from VAPI's response. Handles multiple shapes:
      - {"output":[{"role":"assistant","content":"..."}]}
      - {"output":[{"type":"message","content":"..."}]}
      - tool calls in output or messages:
          {"output":[{"type":"tool-call","toolName":"...","parameters":{...}}]}
          {"messages":[{"role":"assistant","tool_calls":[...]}]}
    """
    reply_text: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None

    out_list: List[Dict[str, Any]] = data.get("output") or []
    for item in out_list:
        if not isinstance(item, dict):
            continue
        # Common "message" shape
        if "content" in item and isinstance(item.get("content"), str):
            reply_text = item["content"]
        # Some providers expose explicit type
        if item.get("type") in {"tool-call", "function_call"}:
            tool_call = {
                "toolName": item.get("toolName") or item.get("name"),
                "parameters": item.get("parameters") or item.get("arguments") or {},
            }
        # Some shapes nest under "tool_calls" (OpenAI-style)
        if "tool_calls" in item and isinstance(item["tool_calls"], list) and item["tool_calls"]:
            tc = item["tool_calls"][0]
            if isinstance(tc, dict):
                fn = (tc.get("function") or {})
                tool_call = {
                    "toolName": fn.get("name"),
                    "parameters": fn.get("arguments"),
                }

    # Fallback: check messages array for tool_calls/tool role
    msgs: List[Dict[str, Any]] = data.get("messages") or []
    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        if reply_text is None and msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
            reply_text = msg["content"]
        if "tool_calls" in msg and isinstance(msg["tool_calls"], list) and msg["tool_calls"]:
            tc = msg["tool_calls"][0]
            if isinstance(tc, dict):
                fn = (tc.get("function") or {})
                tool_call = {
                    "toolName": fn.get("name"),
                    "parameters": fn.get("arguments"),
                }
        if msg.get("role") == "tool" and reply_text is None:
            # Tool responded textually; surface something human-readable
            c = msg.get("content")
            if isinstance(c, str):
                reply_text = f"[Tool Result] {c}"

    return reply_text, tool_call


async def send_message(user_id: str, assistant_id: str, user_input: str, db):
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "assistantId": assistant_id,
        "input": user_input,
    }

    # Reuse previous chat if we have it
    existing_chat = await db.chats.find_one({"user_id": user_id})
    if existing_chat:
        payload["previousChatId"] = existing_chat["chat_id"]

    # Call VAPI (non-blocking, with sensible timeout)
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, read=20.0, connect=10.0)) as client:
        resp = await client.post(BASE_URL, json=payload, headers=headers)
        # Guard non-200s
        if resp.status_code >= 400:
            return {
                "error": f"VAPI HTTP {resp.status_code}",
                "details": resp.text,
            }
        try:
            data = resp.json()
        except Exception as e:
            return {
                "error": "VAPI returned non-JSON",
                "details": str(e),
                "body": resp.text[:5000],
            }

    chat_id = data.get("id")
    if not chat_id:
        return {"error": "No chatId returned from VAPI", "raw": data}

    # Extract assistant reply and/or tool info safely
    reply_text, tool_call = _extract_reply_and_tool(data)

    # Build messages for storage
    user_msg = {"role": "user", "content": user_input}
    if tool_call:
        assistant_content = f"[Tool Call] {tool_call.get('toolName')} with params {tool_call.get('parameters')}"
    else:
        assistant_content = reply_text or ""

    assistant_msg = {"role": "assistant", "content": assistant_content}

    # Persist without blocking the HTTP response
    async def _persist():
        try:
            now = datetime.utcnow()
            if existing_chat:
                await db.chats.update_one(
                    {"_id": existing_chat["_id"]},
                    {
                        "$set": {"chat_id": chat_id, "updated_at": now},
                        "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
                    },
                )
            else:
                await db.chats.insert_one(
                    {
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "messages": [user_msg, assistant_msg],
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        except Exception as e:
            # Log but don't break the chat flow
            print(f"[Mongo Persist Error] {e}")

    # Fire-and-forget to avoid delaying the reply
    asyncio.create_task(_persist())

    return {
        "chatId": chat_id,
        "reply": reply_text or assistant_msg["content"] or "",
        "toolCall": tool_call,  # let your frontend know if a tool was invoked
        "raw": data,
    }
