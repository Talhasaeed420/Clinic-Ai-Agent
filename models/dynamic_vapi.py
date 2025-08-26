from typing import List, Dict, Optional
from pydantic import BaseModel, Field

# ------------------------------
# Tool Function Schema
# ------------------------------
class ToolFunctionParameters(BaseModel):
    type: str = Field(default="object")
    properties: Dict[str, Dict[str, str]]
    required: List[str]


class ToolFunction(BaseModel):
    name: str
    description: str
    parameters: ToolFunctionParameters


class Tool(BaseModel):
    type: str = Field(default="function")
    function: ToolFunction
    server: Dict[str, str]


# ------------------------------
# Assistant Schema
# ------------------------------
class AssistantVoice(BaseModel):
    provider: str
    voiceId: str


class AssistantTranscriber(BaseModel):
    provider: str
    language: str


class AssistantModelConfig(BaseModel):
    provider: str
    model: str
    toolIds: Optional[List[str]] = []  


class AssistantServer(BaseModel):
    url: str


class AssistantPayload(BaseModel):
    name: str
    firstMessage: str
    voice: AssistantVoice
    transcriber: AssistantTranscriber
    model: AssistantModelConfig
    server: AssistantServer
    
