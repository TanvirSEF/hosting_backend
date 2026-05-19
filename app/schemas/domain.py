# app/schemas/domain.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.domain import DomainStatus

class DomainSearchRequest(BaseModel):
    domain_name: str

class DomainRegisterRequest(BaseModel):
    domain_name: str
    years: Optional[int] = 1

class DomainOrderOut(BaseModel):
    id: int
    user_id: int
    domain_name: str
    status: DomainStatus
    ns1: str
    ns2: str
    expiry_date: datetime

    class Config:
        from_attributes = True