# app/schemas/health.py
from pydantic import BaseModel
from typing import Dict, Any

class SubsystemStatus(BaseModel):
    status: str
    latency_ms: float

class SystemHealthResponse(BaseModel):
    overall_status: str
    timestamp: str
    subsystems: Dict[str, Any]