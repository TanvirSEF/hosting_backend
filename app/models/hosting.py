# app/models/hosting.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Numeric, Boolean
from sqlalchemy.sql import func
from app.database.session import Base
import enum

class HostingStatus(str, enum.Enum):
    PAYMENT_PENDING = "payment_pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    PROVISION_FAILED = "provision_failed"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class HostingPackage(Base):
    __tablename__ = "hosting_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    whm_package_id = Column(String, unique=True, nullable=False)
    price_bdt = Column(Numeric(10, 2), nullable=False)
    billing_period_days = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HostingOrder(Base):
    __tablename__ = "hosting_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    package_id = Column(Integer, ForeignKey("hosting_packages.id"), nullable=True)
    domain = Column(String, nullable=False, index=True)
    package_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    status = Column(Enum(HostingStatus), default=HostingStatus.PAYMENT_PENDING)
    whm_package_id = Column(String, nullable=True)
    provision_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
