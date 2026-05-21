# app/schemas/billing.py
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.models.billing import BillingReason, BillingServiceType, InvoiceStatus, PaymentGateway

class InvoiceCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    days_valid: Optional[int] = Field(default=7, ge=1, le=60)

class InvoiceOut(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    status: InvoiceStatus
    service_type: Optional[BillingServiceType]
    service_id: Optional[int]
    billing_reason: BillingReason
    created_at: datetime
    due_at: datetime
    paid_at: Optional[datetime]
    reminder_sent_at: Optional[datetime] = None
    overdue_processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentVerificationRequest(BaseModel):
    invoice_id: int = Field(gt=0)
    gateway: PaymentGateway
    transaction_id: str = Field(min_length=4, max_length=120)

class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus

class RenewalInvoiceRequest(BaseModel):
    days_valid: int = Field(default=7, ge=1, le=60)

class AutoRenewUpdate(BaseModel):
    auto_renew: bool

class BillingLifecycleRunRequest(BaseModel):
    days_ahead: int = Field(default=7, ge=1, le=60)

class BillingLifecycleRunOut(BaseModel):
    generated_hosting_invoices: int = 0
    generated_domain_invoices: int = 0
    reminders_marked: int = 0
    hosting_suspended: int = 0
    domains_expired: int = 0
