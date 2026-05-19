# app/schemas/hosting.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.models.hosting import HostingStatus

class HostingCreateRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    package_id: int = Field(gt=0)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        clean = value.lower().strip()
        if "/" in clean or " " in clean or "." not in clean:
            raise ValueError("Invalid domain name.")
        return clean

class HostingPackageCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    whm_package_id: str = Field(min_length=2, max_length=100)
    price_bdt: Decimal = Field(gt=0)
    billing_period_days: int = Field(default=30, ge=1, le=366)

class HostingPackageOut(BaseModel):
    id: int
    name: str
    whm_package_id: str
    price_bdt: Decimal
    billing_period_days: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class HostingOrderOut(BaseModel):
    id: int
    user_id: int
    invoice_id: Optional[int]
    package_id: Optional[int]
    domain: str
    package_name: str
    username: Optional[str]
    status: HostingStatus
    provision_error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
