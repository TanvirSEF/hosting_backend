# app/schemas/billing.py
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.models.billing import InvoiceStatus, PaymentGateway

class InvoiceCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    days_valid: Optional[int] = Field(default=7, ge=1, le=60)

class InvoiceOut(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    status: InvoiceStatus
    created_at: datetime
    due_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True

class PaymentVerificationRequest(BaseModel):
    invoice_id: int = Field(gt=0)
    gateway: PaymentGateway
    transaction_id: str = Field(min_length=4, max_length=120)

class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
