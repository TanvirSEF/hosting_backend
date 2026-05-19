from datetime import datetime
from typing import List
from pydantic import BaseModel
from app.models.support import SupportTicketStatus


class SupportTicketCreate(BaseModel):
    subject: str
    message: str
    priority: str = "normal"


class SupportTicketMessageCreate(BaseModel):
    message: str


class SupportTicketStatusUpdate(BaseModel):
    status: SupportTicketStatus


class SupportTicketMessageOut(BaseModel):
    id: int
    ticket_id: int
    sender_user_id: int
    sender_role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketOut(BaseModel):
    id: int
    user_id: int
    subject: str
    status: SupportTicketStatus
    priority: str
    created_at: datetime
    messages: List[SupportTicketMessageOut] = []

    class Config:
        from_attributes = True
