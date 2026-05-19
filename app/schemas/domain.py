# app/schemas/domain.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from app.models.domain import DomainStatus

class DomainSearchRequest(BaseModel):
    domain_name: str = Field(min_length=3, max_length=253)

    @field_validator("domain_name")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        clean = value.lower().strip()
        if "/" in clean or " " in clean or "." not in clean:
            raise ValueError("Invalid domain name.")
        return clean

class DomainRegisterRequest(BaseModel):
    domain_name: str = Field(min_length=3, max_length=253)
    years: Optional[int] = Field(default=1, ge=1, le=10)

    @field_validator("domain_name")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        clean = value.lower().strip()
        if "/" in clean or " " in clean or "." not in clean:
            raise ValueError("Invalid domain name.")
        return clean

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

class DomainStatusUpdate(BaseModel):
    status: DomainStatus
