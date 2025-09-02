from pydantic import BaseModel, Field

class Tool(BaseModel):
    name: str 
    AVAILABLE_TOOL_IDS: str 
