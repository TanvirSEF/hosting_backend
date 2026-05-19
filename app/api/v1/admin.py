# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.automation import AutomationLog
from app.models.user import User
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.models.billing import Invoice, InvoiceStatus
from app.models.domain import UserDomain
from app.schemas.user import UserOut
from app.schemas.hosting import HostingOrderOut, HostingPackageCreate, HostingPackageOut
from app.schemas.billing import InvoiceOut, InvoiceStatusUpdate
from app.schemas.domain import DomainOrderOut, DomainStatusUpdate
from app.schemas.admin import AdminDashboardStats, AutomationLogOut
from app.api.admin_deps import require_admin_user  # Import our role-based guard
from app.tasks.hosting_tasks import provision_cpanel_async

router = APIRouter()

@router.get("/metrics", response_model=AdminDashboardStats)
def get_admin_dashboard_overview(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    Returns high-level system monitoring statistics for the Admin spike layout interface.
    """
    user_count = db.query(User).count()
    hosting_count = db.query(HostingOrder).count()
    pending_count = (
        db.query(HostingOrder)
        .filter(HostingOrder.status.in_([HostingStatus.PAYMENT_PENDING, HostingStatus.PROVISIONING]))
        .count()
    )
    
    # Calculate total revenue from all PAID invoices safely
    paid_invoices = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID).all()
    total_revenue = sum(inv.amount for inv in paid_invoices) if paid_invoices else 0.00
    
    return {
        "total_users": user_count,
        "total_hosting_orders": hosting_count,
        "total_revenue_bdt": total_revenue,
        "pending_provisions": pending_count
    }

@router.get("/users", response_model=List[UserOut])
def list_all_registered_clients(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    Fetches and arrays all user rows currently saved inside the platform database.
    """
    return db.query(User).all()

@router.post("/hosting-packages", response_model=HostingPackageOut, status_code=status.HTTP_201_CREATED)
def create_hosting_package(
    payload: HostingPackageCreate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    existing = (
        db.query(HostingPackage)
        .filter(
            (HostingPackage.name == payload.name)
            | (HostingPackage.whm_package_id == payload.whm_package_id)
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Hosting package already exists.")

    package = HostingPackage(
        name=payload.name,
        whm_package_id=payload.whm_package_id,
        price_bdt=payload.price_bdt,
        billing_period_days=payload.billing_period_days,
        is_active=True,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package

@router.get("/hosting-packages", response_model=List[HostingPackageOut])
def list_hosting_packages(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(HostingPackage).all()

@router.get("/hosting-orders", response_model=List[HostingOrderOut])
def list_hosting_orders(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(HostingOrder).order_by(HostingOrder.id.desc()).all()

@router.get("/hosting/{order_id}", response_model=HostingOrderOut)
def get_hosting_order(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    order = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order entry not found.")
    return order

@router.post("/hosting/{order_id}/retry-provisioning", response_model=HostingOrderOut)
def retry_failed_provisioning(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    order = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order entry not found.")
    if order.status != HostingStatus.PROVISION_FAILED:
        raise HTTPException(status_code=400, detail="Only failed provisioning orders can be retried.")

    order.status = HostingStatus.PROVISIONING
    order.provision_error = None
    db.commit()

    try:
        provision_cpanel_async.delay(order.id, "automated-client@nexhost.com")
    except Exception as exc:
        order.status = HostingStatus.PROVISION_FAILED
        order.provision_error = f"Failed to queue provisioning retry: {exc}"
        db.commit()
        raise HTTPException(status_code=503, detail=order.provision_error)

    db.refresh(order)
    return order

@router.get("/automation-logs", response_model=List[AutomationLogOut])
def list_automation_logs(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(AutomationLog).order_by(AutomationLog.id.desc()).limit(100).all()

@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(Invoice).order_by(Invoice.id.desc()).all()

@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice

@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: int,
    payload: InvoiceStatusUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    invoice.status = payload.status
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/domains", response_model=List[DomainOrderOut])
def list_domains(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(UserDomain).order_by(UserDomain.id.desc()).all()

@router.get("/domains/{domain_id}", response_model=DomainOrderOut)
def get_domain(
    domain_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    domain = db.query(UserDomain).filter(UserDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain record not found.")
    return domain

@router.put("/domains/{domain_id}/status", response_model=DomainOrderOut)
def update_domain_status(
    domain_id: int,
    payload: DomainStatusUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    domain = db.query(UserDomain).filter(UserDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain record not found.")
    domain.status = payload.status
    db.commit()
    db.refresh(domain)
    return domain

@router.put("/hosting/{order_id}/toggle-status", response_model=HostingOrderOut)
def administrative_hosting_status_override(
    order_id: int,
    new_status: HostingStatus,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    Allows admin operators to manually change any hosting service status row directly.
    """
    order = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order entry not found.")
        
    # Update relational target record mapping fields safely
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
