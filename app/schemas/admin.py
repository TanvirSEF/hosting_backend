# app/schemas/admin.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

class AdminDashboardStats(BaseModel):
    total_users: int
    total_hosting_orders: int
    total_revenue_bdt: Decimal
    pending_provisions: int


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
