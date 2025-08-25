from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class VoiceConfig(BaseModel):
    provider: Optional[str] = None
    voiceId: Optional[str] = None
    model: Optional[str] = None

class TranscriberConfig(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    language: Optional[str] = None

class ModelConfig(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    systemPrompt: Optional[str] = None
    messages: Optional[List[Dict]] = None

class ToolParameter(BaseModel):
    type: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None

class ToolConfig(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[ToolParameter] = None

class BotConfig(BaseModel):
    name: Optional[str] = None
    model: Optional[ModelConfig] = None
    voice: Optional[VoiceConfig] = None
    transcriber: Optional[TranscriberConfig] = None
    tools: Optional[List[ToolConfig]] = None
