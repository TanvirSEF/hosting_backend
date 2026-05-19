# app/models/hosting.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from app.database.session import Base
import enum

class HostingStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class HostingOrder(Base):
    __tablename__ = "hosting_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain = Column(String, nullable=False, index=True)
    package_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    status = Column(Enum(HostingStatus), default=HostingStatus.PENDING)
    whm_package_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())