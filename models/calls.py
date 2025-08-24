from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from bson import ObjectId
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        def validate(value):
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                try:
                    return ObjectId(value)
                except Exception:
                    raise ValueError("Invalid ObjectId")
            raise ValueError("Must be string or ObjectId")

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.str_schema()
            ])
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler):
        return handler(core_schema.str_schema())

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

class CallAnalysis(BaseModel):
    summary: Optional[str] = None
    successEvaluation: Optional[str] = None

class CallArtifact(BaseModel):
    messages: Optional[List[Dict]] = None
    messagesOpenAIFormatted: Optional[List[Dict]] = None
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    stereoRecordingUrl: Optional[str] = None

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
        json_encoders={ObjectId: str},
        populate_by_name=True
    )