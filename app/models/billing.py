# app/models/billing.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Enum
from sqlalchemy.sql import func
from app.database.session import Base
import enum

class InvoiceStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    CANCELLED = "cancelled"

class PaymentGateway(str, enum.Enum):
    BKASH = "bkash"
    NAGAD = "nagad"
    SSLCOMMERZ = "sslcommerz"

class BillingServiceType(str, enum.Enum):
    HOSTING = "hosting"
    DOMAIN = "domain"

class BillingReason(str, enum.Enum):
    MANUAL = "manual"
    INITIAL_PURCHASE = "initial_purchase"
    RENEWAL = "renewal"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.UNPAID)
    service_type = Column(Enum(BillingServiceType), nullable=True, index=True)
    service_id = Column(Integer, nullable=True, index=True)
    billing_reason = Column(Enum(BillingReason), default=BillingReason.MANUAL, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    due_at = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    overdue_processed_at = Column(DateTime(timezone=True), nullable=True)

class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    gateway = Column(Enum(PaymentGateway), nullable=False)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    raw_response = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
