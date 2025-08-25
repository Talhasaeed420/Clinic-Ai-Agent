from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from .object_id import PyObjectId
from .artifacts import CallAnalysis, CallArtifact
from .metrics import CostBreakdown, PerformanceMetrics
from .info import CallInfo, AssistantInfo
from .configs import BotConfig

class VapiCallReport(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    timestamp: Optional[int] = None
    type: Optional[str] = None
    analysis: Optional[CallAnalysis] = None
    artifact: Optional[CallArtifact] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None
    endedReason: Optional[str] = None
    cost: Optional[float] = None
    costBreakdown: Optional[CostBreakdown] = None
    costs: Optional[List[Dict]] = None
    durationMs: Optional[int] = None
    durationSeconds: Optional[float] = None
    durationMinutes: Optional[float] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    stereoRecordingUrl: Optional[str] = None
    nodes: Optional[List] = None
    variables: Optional[Dict] = None
    variableValues: Optional[Dict] = None
    performanceMetrics: Optional[PerformanceMetrics] = None
    call: Optional[CallInfo] = None
    assistant: Optional[AssistantInfo] = None
    botConfig: Optional[BotConfig] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
        populate_by_name=True
    )
