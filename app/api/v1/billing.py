# app/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database.session import get_db
from app.models.billing import Invoice, PaymentLog, InvoiceStatus
from app.models.hosting import HostingOrder, HostingStatus
from app.schemas.billing import InvoiceCreate, InvoiceOut, PaymentVerificationRequest
from app.api.deps import get_current_user_id 
from app.services.payment_gateway import payment_gateway_service
from app.tasks.hosting_tasks import provision_cpanel_async

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

    gateway_result = payment_gateway_service.verify_manual_payment(
        gateway=payload.gateway,
        transaction_id=payload.transaction_id,
        amount=invoice.amount,
    )
    if not gateway_result.get("success"):
        raise HTTPException(status_code=400, detail="Payment verification failed.")

    payment_log = PaymentLog(
        invoice_id=invoice.id,
        gateway=payload.gateway,
        transaction_id=payload.transaction_id,
        raw_response=str(gateway_result)
    )
    db.add(payment_log)
    
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = datetime.utcnow()

    hosting_order = (
        db.query(HostingOrder)
        .filter(
            HostingOrder.invoice_id == invoice.id,
            HostingOrder.status == HostingStatus.PAYMENT_PENDING,
        )
        .first()
    )
    queued_order_id = None
    if hosting_order:
        hosting_order.status = HostingStatus.PROVISIONING
        hosting_order.provision_error = None
        db.flush()
        provision_cpanel_async.delay(hosting_order.id, "automated-client@nexhost.com")
        queued_order_id = hosting_order.id
    
    db.commit()

    return {
        "status": "success",
        "message": f"Payment via {payload.gateway.upper()} verified successfully! Invoice #{invoice.id} status updated to PAID.",
        "queued_hosting_order_id": queued_order_id,
    }

@router.post("/webhooks/{gateway}")
async def payment_webhook_placeholder(gateway: str):
    """
    Reserved endpoint for SSLCommerz, bKash, and Nagad webhook integrations.
    Real provider signature verification and idempotent processing will be added later.
    """
    supported = {"sslcommerz", "bkash", "nagad"}
    if gateway not in supported:
        raise HTTPException(status_code=404, detail="Unsupported payment gateway.")

    return {
        "status": "placeholder",
        "gateway": gateway,
        "message": "Webhook endpoint reserved for future real payment gateway integration.",
    }
