# app/api/v1/email.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import EmailAccount
from app.schemas.hosting_tools import EmailAccountCreate, EmailAccountOut, EmailPasswordUpdate
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action

router = APIRouter()


@router.get("/{hosting_order_id}/accounts", response_model=List[EmailAccountOut])
def list_email_accounts(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(EmailAccount).filter(EmailAccount.hosting_order_id == hosting_order_id).all()


@router.post("/{hosting_order_id}/accounts", response_model=EmailAccountOut, status_code=status.HTTP_201_CREATED)
def create_email_account(
    hosting_order_id: int,
    payload: EmailAccountCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    order = get_owned_hosting_order(db, hosting_order_id, user_id)
    email_address = f"{payload.local_part}@{order.domain}"
    existing = db.query(EmailAccount).filter(EmailAccount.email_address == email_address).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email account already exists.")
    account = EmailAccount(hosting_order_id=hosting_order_id, email_address=email_address, quota_mb=payload.quota_mb)
    db.add(account)
    log_tool_action(db, hosting_order_id, "email", "create_account")
    db.commit()
    db.refresh(account)
    return account


@router.put("/accounts/{account_id}/password", response_model=EmailAccountOut)
def update_email_password(
    account_id: int,
    payload: EmailPasswordUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found.")
    get_owned_hosting_order(db, account.hosting_order_id, user_id)
    log_tool_action(db, account.hosting_order_id, "email", "reset_password")
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}")
def delete_email_account(account_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    account = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found.")
    get_owned_hosting_order(db, account.hosting_order_id, user_id)
    hosting_order_id = account.hosting_order_id
    db.delete(account)
    log_tool_action(db, hosting_order_id, "email", "delete_account")
    db.commit()
    return {"status": "deleted"}
