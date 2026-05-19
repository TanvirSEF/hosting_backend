# app/schemas/admin.py
from pydantic import BaseModel
from decimal import Decimal

class AdminDashboardStats(BaseModel):
    total_users: int
    total_hosting_orders: int
    total_revenue_bdt: Decimal
    pending_provisions: int