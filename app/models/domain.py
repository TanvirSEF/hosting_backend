# app/models/domain.py
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from app.database.session import Base
import enum

class DomainStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"

class UserDomain(Base):
    __tablename__ = "user_domains"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain_name = Column(String, unique=True, index=True, nullable=False) # e.g., typescale.com
    status = Column(Enum(DomainStatus), default=DomainStatus.PENDING)
    
    # Nameserver tracking configuration fields
    ns1 = Column(String, default="ns1.nexhost.com")
    ns2 = Column(String, default="ns2.nexhost.com")
    auto_renew = Column(Boolean, default=True, nullable=False)
    
    # Important automation milestone tracking timestamps
    registration_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
