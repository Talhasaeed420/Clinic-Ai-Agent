from typing import List, Optional, Dict
from pydantic import BaseModel

class CostBreakdown(BaseModel):
    stt: Optional[float] = None
    llm: Optional[float] = None
    tts: Optional[float] = None
    vapi: Optional[float] = None
    chat: Optional[float] = None
    transport: Optional[float] = None
    total: Optional[float] = None
    llmPromptTokens: Optional[int] = None
    llmCompletionTokens: Optional[int] = None
    ttsCharacters: Optional[int] = None

class PerformanceMetrics(BaseModel):
    turnLatencies: Optional[List[Dict]] = None
    modelLatencyAverage: Optional[int] = None
    voiceLatencyAverage: Optional[int] = None
    transcriberLatencyAverage: Optional[int] = None
    turnLatencyAverage: Optional[int] = None
