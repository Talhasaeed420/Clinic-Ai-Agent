from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from .configs import VoiceConfig, ModelConfig, TranscriberConfig

class CallInfo(BaseModel):
    id: Optional[str] = None
    orgId: Optional[str] = None
    createdAt: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None

class AssistantInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    voice: Optional[VoiceConfig] = None
    model: Optional[ModelConfig] = None
    transcriber: Optional[TranscriberConfig] = None
