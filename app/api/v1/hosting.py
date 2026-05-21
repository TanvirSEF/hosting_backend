# app/api/v1/hosting.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database.session import get_db
from app.models.billing import BillingReason, BillingServiceType, Invoice, InvoiceStatus
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.schemas.hosting import HostingCreateRequest, HostingOrderOut, HostingPackageOut
from app.api.deps import get_current_user_id

router = APIRouter()

@router.get("/packages", response_model=List[HostingPackageOut])
def list_active_hosting_packages(db: Session = Depends(get_db)):
    return db.query(HostingPackage).filter(HostingPackage.is_active == True).all()

@router.post("/orders", response_model=HostingOrderOut, status_code=status.HTTP_201_CREATED)
def create_hosting_order(
    payload: HostingCreateRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Creates a hosting order and linked unpaid invoice. Provisioning starts only after payment.
    """
    package = (
        db.query(HostingPackage)
        .filter(HostingPackage.id == payload.package_id, HostingPackage.is_active == True)
        .first()
    )
    if not package:
        raise HTTPException(status_code=404, detail="Active hosting package not found.")

    existing_order = (
        db.query(HostingOrder)
        .filter(
            HostingOrder.domain == payload.domain,
            HostingOrder.status != HostingStatus.TERMINATED,
        )
        .first()
    )
    if existing_order:
        raise HTTPException(status_code=400, detail="This domain already has an active hosting order.")

    invoice = Invoice(
        user_id=user_id,
        amount=package.price_bdt,
        status=InvoiceStatus.UNPAID,
        service_type=BillingServiceType.HOSTING,
        billing_reason=BillingReason.INITIAL_PURCHASE,
        due_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invoice)
    db.flush()

    new_order = HostingOrder(
        user_id=user_id,
        invoice_id=invoice.id,
        package_id=package.id,
        domain=payload.domain,
        package_name=package.name,
        status=HostingStatus.PAYMENT_PENDING,
        whm_package_id=package.whm_package_id,
    )
    db.add(new_order)
    db.flush()
    invoice.service_id = new_order.id
    db.commit()
    db.refresh(new_order)

    return new_order

@router.post("/provision", response_model=HostingOrderOut, status_code=status.HTTP_201_CREATED)
def provision_hosting(
    payload: HostingCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Backward-compatible alias for creating an unpaid hosting order.
    """
    return create_hosting_order(payload=payload, user_id=user_id, db=db)

@router.get("/my-services", response_model=List[HostingOrderOut])
def get_user_services(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Returns array containing services owned by current active session client context."""
    services = db.query(HostingOrder).filter(HostingOrder.user_id == user_id).all()
    return services
