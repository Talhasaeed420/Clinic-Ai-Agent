from pydantic import BaseModel, Field

class Tool(BaseModel):
    name: str 
    tool_id: str 
