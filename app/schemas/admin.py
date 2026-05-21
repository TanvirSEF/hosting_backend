# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.models.hosting import HostingStatus

class AdminDashboardStats(BaseModel):
    total_users: int
    total_hosting_orders: int
    total_revenue_bdt: Decimal
    pending_provisions: int


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, max_length=30)


class AdminUserActiveUpdate(BaseModel):
    is_active: bool


class AdminUserPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class AdminUserRoleUpdate(BaseModel):
    is_admin: bool


class HostingPackageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    whm_package_id: Optional[str] = Field(default=None, min_length=2, max_length=100)
    price_bdt: Optional[Decimal] = Field(default=None, gt=0)
    billing_period_days: Optional[int] = Field(default=None, ge=1, le=366)
    is_active: Optional[bool] = None


class DomainNameserverUpdate(BaseModel):
    ns1: str = Field(min_length=3, max_length=255)
    ns2: str = Field(min_length=3, max_length=255)


class DomainRenewRequest(BaseModel):
    years: int = Field(default=1, ge=1, le=10)


class HostingStatusOverride(BaseModel):
    status: HostingStatus


class HostingSuspendRequest(BaseModel):
    reason: str = Field(default="Administrative action", min_length=2, max_length=255)


class HostingChangePackageRequest(BaseModel):
    package_id: int = Field(gt=0)


class AutomationLogOut(BaseModel):
    id: int
    hosting_order_id: Optional[int]
    action: str
    status: str
    message: Optional[str]
    raw_response: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
