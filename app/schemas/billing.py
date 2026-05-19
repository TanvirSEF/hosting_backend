# app/schemas/billing.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.models.billing import InvoiceStatus, PaymentGateway

class InvoiceCreate(BaseModel):
    amount: Decimal
    days_valid: Optional[int] = 7 

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
    invoice_id: int
    gateway: PaymentGateway
    transaction_id: str  