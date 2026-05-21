# app/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database.session import get_db
from app.models.billing import BillingReason, BillingServiceType, Invoice, PaymentLog, InvoiceStatus
from app.models.domain import UserDomain
from app.models.hosting import HostingOrder, HostingStatus
from app.schemas.billing import AutoRenewUpdate, InvoiceCreate, InvoiceOut, PaymentVerificationRequest, RenewalInvoiceRequest
from app.api.deps import get_current_user_id 
from app.services.billing_lifecycle import (
    apply_paid_invoice_lifecycle,
    create_domain_renewal_invoice,
    create_hosting_renewal_invoice,
)
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
        billing_reason=BillingReason.MANUAL,
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
    lifecycle_result = apply_paid_invoice_lifecycle(db, invoice)

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
        try:
            provision_cpanel_async.delay(hosting_order.id, "automated-client@nexhost.com")
        except Exception as exc:
            hosting_order.status = HostingStatus.PROVISION_FAILED
            hosting_order.provision_error = f"Failed to queue provisioning task: {exc}"
            db.commit()
            raise HTTPException(status_code=503, detail=hosting_order.provision_error)
        queued_order_id = hosting_order.id
    
    db.commit()

    return {
        "status": "success",
        "message": f"Payment via {payload.gateway.upper()} verified successfully! Invoice #{invoice.id} status updated to PAID.",
        "queued_hosting_order_id": queued_order_id,
        "lifecycle_result": lifecycle_result,
    }

@router.post("/renew/hosting/{hosting_order_id}", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_hosting_renewal(
    hosting_order_id: int,
    payload: RenewalInvoiceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    order = (
        db.query(HostingOrder)
        .filter(HostingOrder.id == hosting_order_id, HostingOrder.user_id == user_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Hosting service not found.")
    if order.status == HostingStatus.TERMINATED:
        raise HTTPException(status_code=400, detail="Terminated hosting services cannot be renewed.")
    try:
        invoice = create_hosting_renewal_invoice(db, order, days_valid=payload.days_valid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(invoice)
    return invoice

@router.post("/renew/domain/{domain_id}", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_domain_renewal(
    domain_id: int,
    payload: RenewalInvoiceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    domain = db.query(UserDomain).filter(UserDomain.id == domain_id, UserDomain.user_id == user_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found.")
    invoice = create_domain_renewal_invoice(db, domain, days_valid=payload.days_valid)
    db.commit()
    db.refresh(invoice)
    return invoice

@router.put("/auto-renew/hosting/{hosting_order_id}")
def update_hosting_auto_renew(
    hosting_order_id: int,
    payload: AutoRenewUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    order = (
        db.query(HostingOrder)
        .filter(HostingOrder.id == hosting_order_id, HostingOrder.user_id == user_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Hosting service not found.")
    order.auto_renew = payload.auto_renew
    db.commit()
    return {"hosting_order_id": order.id, "auto_renew": order.auto_renew}

@router.put("/auto-renew/domain/{domain_id}")
def update_domain_auto_renew(
    domain_id: int,
    payload: AutoRenewUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    domain = db.query(UserDomain).filter(UserDomain.id == domain_id, UserDomain.user_id == user_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found.")
    domain.auto_renew = payload.auto_renew
    db.commit()
    return {"domain_id": domain.id, "auto_renew": domain.auto_renew}

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
