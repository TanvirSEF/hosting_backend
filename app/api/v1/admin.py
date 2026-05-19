# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.user import User
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.models.billing import Invoice, InvoiceStatus
from app.schemas.user import UserOut
from app.schemas.hosting import HostingOrderOut, HostingPackageCreate, HostingPackageOut
from app.schemas.admin import AdminDashboardStats
from app.api.admin_deps import require_admin_user  # Import our role-based guard

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
    pending_count = db.query(HostingOrder).filter(HostingOrder.status == HostingStatus.PENDING).count()
    
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
