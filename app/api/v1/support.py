# app/api/v1/support.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.support import SupportTicket, SupportTicketMessage, SupportTicketStatus
from app.models.user import User
from app.schemas.support import SupportTicketCreate, SupportTicketMessageCreate, SupportTicketOut

router = APIRouter()


def ticket_with_messages(db: Session, ticket: SupportTicket) -> dict:
    messages = (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .order_by(SupportTicketMessage.id.asc())
        .all()
    )
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "created_at": ticket.created_at,
        "messages": messages,
    }


@router.post("/tickets", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = SupportTicket(
        user_id=current_user.id,
        subject=payload.subject,
        priority=payload.priority,
        status=SupportTicketStatus.WAITING_ADMIN,
    )
    db.add(ticket)
    db.flush()
    db.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            sender_role="customer",
            message=payload.message,
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket_with_messages(db, ticket)


@router.get("/tickets", response_model=List[SupportTicketOut])
def list_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.id.desc())
        .all()
    )
    return [ticket_with_messages(db, ticket) for ticket in tickets]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketOut)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    return ticket_with_messages(db, ticket)


@router.post("/tickets/{ticket_id}/messages", response_model=SupportTicketOut)
def add_ticket_message(
    ticket_id: int,
    payload: SupportTicketMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    if ticket.status == SupportTicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Closed tickets cannot receive new messages.")

    db.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            sender_role="customer",
            message=payload.message,
        )
    )
    ticket.status = SupportTicketStatus.WAITING_ADMIN
    db.commit()
    db.refresh(ticket)
    return ticket_with_messages(db, ticket)
