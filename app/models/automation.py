# app/models/automation.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database.session import Base


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=True)
    raw_response = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
