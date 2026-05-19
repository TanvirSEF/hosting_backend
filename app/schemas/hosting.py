# app/schemas/hosting.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.models.hosting import HostingStatus

class HostingCreateRequest(BaseModel):
    domain: str
    package_id: int

class HostingPackageCreate(BaseModel):
    name: str
    whm_package_id: str
    price_bdt: Decimal
    billing_period_days: int = 30

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
