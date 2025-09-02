from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from typing import List
from models.tool_model import Tool
from fastapi import APIRouter, Request, HTTPException


load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")


router = APIRouter()
# MongoDB client
client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
tools_collection = db["tools"]

#--------------Get tools--------------
@router.get("/get-tools", response_model=List[Tool])
async def get_tools():
    tools = await tools_collection.find().to_list(length=None)
    return tools

#-------------Post tool------------------

@router.post("/post-tool", response_model=Tool)
async def post_tool(tool: Tool):
    existing = await tools_collection.find_one({"name": tool.name})
    if existing:
        raise HTTPException(status_code=400, detail="Tool already exists")
    result = await tools_collection.insert_one(tool.dict())
    if result.inserted_id:
        return tool
    raise HTTPException(status_code=500, detail="Failed to insert tool")


#-------------Update tool id-------------
@router.put("/update-tool/{name}", response_model=Tool)
async def update_tool(name: str, tool: Tool):
    existing = await tools_collection.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Tool not found")
    await tools_collection.update_one({"name": name}, {"$set": tool.dict()})
    return tool


#-------------Delete tool-----------------
@router.delete("/delete-tool/{name}", response_model=Tool)
async def delete_tool(name: str):
    existing = await tools_collection.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Tool not found")
    await tools_collection.delete_one({"name": name})
    return existing