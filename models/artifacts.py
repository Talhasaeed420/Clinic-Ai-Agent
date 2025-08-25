from typing import List, Optional, Dict
from pydantic import BaseModel

class CallAnalysis(BaseModel):
    summary: Optional[str] = None
    successEvaluation: Optional[str] = None

class CallArtifact(BaseModel):
    messages: Optional[List[Dict]] = None
    messagesOpenAIFormatted: Optional[List[Dict]] = None
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    stereoRecordingUrl: Optional[str] = None
