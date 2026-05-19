# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.automation import AutomationLog
from app.models.security import AdminTwoFactorSetting, AuditLog, ProviderCredential
from app.models.user import User
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.models.billing import Invoice, InvoiceStatus
from app.models.domain import UserDomain
from app.models.support import SupportTicket, SupportTicketMessage, SupportTicketStatus
from app.schemas.user import UserOut
from app.schemas.hosting import HostingOrderOut, HostingPackageCreate, HostingPackageOut
from app.schemas.billing import InvoiceOut, InvoiceStatusUpdate
from app.schemas.domain import DomainOrderOut, DomainStatusUpdate
from app.schemas.support import SupportTicketMessageCreate, SupportTicketOut, SupportTicketStatusUpdate
from app.schemas.admin import AdminDashboardStats, AutomationLogOut
from app.schemas.security import (
    AuditLogOut,
    ProviderCredentialCreate,
    ProviderCredentialOut,
    TwoFactorSetupOut,
    TwoFactorUpdateRequest,
)
from app.api.admin_deps import require_admin_user  # Import our role-based guard
from app.services.audit import write_audit_log
from app.services.credential_crypto import encrypt_secret
from app.tasks.hosting_tasks import provision_cpanel_async
from app.tasks.hosting_tool_tasks import sync_usage_mock

router = APIRouter()


def support_ticket_with_messages(db: Session, ticket: SupportTicket) -> dict:
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

@router.get("/audit-logs", response_model=List[AuditLogOut])
def list_audit_logs(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()

@router.post("/security/2fa/setup", response_model=TwoFactorSetupOut)
def setup_admin_two_factor(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    setting = db.query(AdminTwoFactorSetting).filter(AdminTwoFactorSetting.user_id == admin.id).first()
    if not setting:
        setting = AdminTwoFactorSetting(user_id=admin.id, is_enabled=False, secret_hint="SIMULATED-2FA")
        db.add(setting)
    write_audit_log(db, "admin.2fa.setup", admin.id, "user", str(admin.id), "Admin 2FA setup placeholder created.")
    db.commit()
    return {
        "enabled": setting.is_enabled,
        "method": setting.method,
        "secret_hint": setting.secret_hint or "SIMULATED-2FA",
        "message": "2FA placeholder ready. Use code 000000 to enable in local mock mode.",
    }

@router.post("/security/2fa/enable", response_model=TwoFactorSetupOut)
def enable_admin_two_factor(
    payload: TwoFactorUpdateRequest,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    if payload.code != "000000":
        raise HTTPException(status_code=400, detail="Invalid 2FA code for mock setup.")
    setting = db.query(AdminTwoFactorSetting).filter(AdminTwoFactorSetting.user_id == admin.id).first()
    if not setting:
        setting = AdminTwoFactorSetting(user_id=admin.id, secret_hint="SIMULATED-2FA")
        db.add(setting)
    setting.is_enabled = True
    write_audit_log(db, "admin.2fa.enable", admin.id, "user", str(admin.id), "Admin 2FA placeholder enabled.")
    db.commit()
    return {
        "enabled": setting.is_enabled,
        "method": setting.method,
        "secret_hint": setting.secret_hint or "SIMULATED-2FA",
        "message": "2FA placeholder enabled.",
    }

@router.post("/security/2fa/disable", response_model=TwoFactorSetupOut)
def disable_admin_two_factor(
    payload: TwoFactorUpdateRequest,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    if payload.code != "000000":
        raise HTTPException(status_code=400, detail="Invalid 2FA code for mock setup.")
    setting = db.query(AdminTwoFactorSetting).filter(AdminTwoFactorSetting.user_id == admin.id).first()
    if not setting:
        setting = AdminTwoFactorSetting(user_id=admin.id, secret_hint="SIMULATED-2FA")
        db.add(setting)
    setting.is_enabled = False
    write_audit_log(db, "admin.2fa.disable", admin.id, "user", str(admin.id), "Admin 2FA placeholder disabled.")
    db.commit()
    return {
        "enabled": setting.is_enabled,
        "method": setting.method,
        "secret_hint": setting.secret_hint or "SIMULATED-2FA",
        "message": "2FA placeholder disabled.",
    }

@router.post("/provider-credentials", response_model=ProviderCredentialOut, status_code=status.HTTP_201_CREATED)
def create_provider_credential(
    payload: ProviderCredentialCreate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    existing = db.query(ProviderCredential).filter(ProviderCredential.provider_name == payload.provider_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Provider credential already exists.")
    credential = ProviderCredential(
        provider_name=payload.provider_name,
        credential_type=payload.credential_type,
        encrypted_secret=encrypt_secret(payload.secret),
        created_by_user_id=admin.id,
        is_active=True,
    )
    db.add(credential)
    write_audit_log(db, "admin.provider_credential.create", admin.id, "provider_credential", payload.provider_name)
    db.commit()
    db.refresh(credential)
    return credential

@router.get("/provider-credentials", response_model=List[ProviderCredentialOut])
def list_provider_credentials(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    return db.query(ProviderCredential).order_by(ProviderCredential.id.desc()).all()

@router.get("/support/tickets", response_model=List[SupportTicketOut])
def list_support_tickets(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    tickets = db.query(SupportTicket).order_by(SupportTicket.id.desc()).all()
    return [support_ticket_with_messages(db, ticket) for ticket in tickets]

@router.put("/support/tickets/{ticket_id}/status", response_model=SupportTicketOut)
def update_support_ticket_status(
    ticket_id: int,
    payload: SupportTicketStatusUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    return support_ticket_with_messages(db, ticket)

@router.post("/support/tickets/{ticket_id}/messages", response_model=SupportTicketOut)
def add_admin_support_message(
    ticket_id: int,
    payload: SupportTicketMessageCreate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    if ticket.status == SupportTicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Closed tickets cannot receive new messages.")
    db.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            sender_user_id=admin.id,
            sender_role="admin",
            message=payload.message,
        )
    )
    ticket.status = SupportTicketStatus.WAITING_CUSTOMER
    db.commit()
    db.refresh(ticket)
    return support_ticket_with_messages(db, ticket)

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

@router.post("/usage/{hosting_order_id}/sync")
def sync_hosting_usage(
    hosting_order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = db.query(HostingOrder).filter(HostingOrder.id == hosting_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order not found.")
    try:
        sync_usage_mock.delay(order.id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to queue usage sync: {exc}")
    return {"status": "queued", "hosting_order_id": order.id}

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
