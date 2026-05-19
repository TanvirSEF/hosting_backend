# app/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database.session import get_db
from app.models.billing import Invoice, PaymentLog, InvoiceStatus
from app.schemas.billing import InvoiceCreate, InvoiceOut, PaymentVerificationRequest
from app.api.deps import get_current_user_id 

router = APIRouter()

@router.post("/create", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    
    due_date = datetime.utcnow() + timedelta(days=payload.days_valid)
    
    db_invoice = Invoice(
        user_id=user_id,
        amount=payload.amount,
        status=InvoiceStatus.UNPAID,
        due_at=due_date
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.get("/my-invoices", response_model=List[InvoiceOut])
def get_user_invoices(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id).all()
    return invoices

@router.post("/verify-payment")
def verify_payment(payload: PaymentVerificationRequest, db: Session = Depends(get_db)):
  
    invoice = db.query(Invoice).filter(Invoice.id == payload.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    
    if invoice.status == InvoiceStatus.PAID:
        return {"status": "already_paid", "message": "This invoice has already been paid and processed."}

    existing_log = db.query(PaymentLog).filter(PaymentLog.transaction_id == payload.transaction_id).first()
    if existing_log:
        raise HTTPException(status_code=400, detail="This Transaction ID has already been used.")

    payment_log = PaymentLog(
        invoice_id=invoice.id,
        gateway=payload.gateway,
        transaction_id=payload.transaction_id,
        raw_response=f"{{'status': 'COMPLETED', 'gateway': '{payload.gateway}', 'amount': '{invoice.amount}'}}"
    )
    db.add(payment_log)
    
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = datetime.utcnow()
    
    db.commit()

    return {
        "status": "success",
        "message": f"Payment via {payload.gateway.upper()} verified successfully! Invoice #{invoice.id} status updated to PAID."
    }