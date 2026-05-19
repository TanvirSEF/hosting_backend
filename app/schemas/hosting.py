# app/schemas/hosting.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.hosting import HostingStatus

class HostingCreateRequest(BaseModel):
    domain: str        
    package_name: str  

class HostingOrderOut(BaseModel):
    id: int
    user_id: int
    domain: str
    package_name: str
    username: Optional[str]
    status: HostingStatus
    created_at: datetime

    class Config:
        from_attributes = True