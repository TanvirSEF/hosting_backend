# app/api/v1/admin.py
from datetime import datetime, timedelta
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
from app.schemas.admin import (
    AdminDashboardStats,
    AdminUserActiveUpdate,
    AdminUserPasswordReset,
    AdminUserRoleUpdate,
    AdminUserUpdate,
    AutomationLogOut,
    DomainNameserverUpdate,
    DomainRenewRequest,
    HostingChangePackageRequest,
    HostingPackageUpdate,
    HostingStatusOverride,
    HostingSuspendRequest,
)
from app.schemas.security import (
    AuditLogOut,
    ProviderCredentialCreate,
    ProviderCredentialOut,
    TwoFactorSetupOut,
    TwoFactorUpdateRequest,
)
from app.api.admin_deps import require_admin_user  # Import our role-based guard
from app.core.security import get_password_hash
from app.services.audit import write_audit_log
from app.services.credential_crypto import encrypt_secret
from app.services.domain_provider import domain_provider
from app.services.whm import whm_service
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


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def get_package_or_404(db: Session, package_id: int) -> HostingPackage:
    package = db.query(HostingPackage).filter(HostingPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Hosting package not found.")
    return package


def get_order_or_404(db: Session, order_id: int) -> HostingOrder:
    order = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order entry not found.")
    return order


def get_domain_or_404(db: Session, domain_id: int) -> UserDomain:
    domain = db.query(UserDomain).filter(UserDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain record not found.")
    return domain


def ensure_provider_success(result: dict, action: str) -> None:
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error") or result.get("message") or f"{action} provider action failed.",
        )


def require_cpanel_username(order: HostingOrder) -> str:
    if not order.username:
        raise HTTPException(status_code=400, detail="Hosting order does not have a cPanel username yet.")
    return order.username

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

@router.put("/users/{user_id}", response_model=UserOut)
def update_user_profile(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return user

    if "email" in updates:
        existing = db.query(User).filter(User.email == updates["email"], User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="This email is already registered.")
    if "phone_number" in updates and updates["phone_number"]:
        existing = db.query(User).filter(User.phone_number == updates["phone_number"], User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="This phone number is already registered.")

    changes = []
    for field, value in updates.items():
        old_value = getattr(user, field)
        if old_value != value:
            changes.append(f"{field}: {old_value} -> {value}")
            setattr(user, field, value)

    if changes:
        write_audit_log(
            db,
            "admin.user.update",
            admin.id,
            "user",
            str(user.id),
            "; ".join(changes),
        )
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/active", response_model=UserOut)
def update_user_active_status(
    user_id: int,
    payload: AdminUserActiveUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Admins cannot disable their own account.")

    old_status = user.is_active
    user.is_active = payload.is_active
    write_audit_log(
        db,
        "admin.user.active_update",
        admin.id,
        "user",
        str(user.id),
        f"is_active: {old_status} -> {user.is_active}",
    )
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/password", response_model=UserOut)
def reset_user_password(
    user_id: int,
    payload: AdminUserPasswordReset,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    user.hashed_password = get_password_hash(payload.password)
    write_audit_log(
        db,
        "admin.user.password_reset",
        admin.id,
        "user",
        str(user.id),
        "Password reset by admin.",
    )
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/admin-role", response_model=UserOut)
def update_user_admin_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    if user.id == admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="Admins cannot demote their own account.")

    old_role = user.is_admin
    user.is_admin = payload.is_admin
    write_audit_log(
        db,
        "admin.user.role_update",
        admin.id,
        "user",
        str(user.id),
        f"is_admin: {old_role} -> {user.is_admin}",
    )
    db.commit()
    db.refresh(user)
    return user

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
    db.flush()
    write_audit_log(
        db,
        "admin.hosting_package.create",
        admin.id,
        "hosting_package",
        str(package.id),
        f"Created package {payload.name} mapped to {payload.whm_package_id}.",
    )
    db.commit()
    db.refresh(package)
    return package

@router.get("/hosting-packages", response_model=List[HostingPackageOut])
def list_hosting_packages(
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    return db.query(HostingPackage).all()

@router.put("/hosting-packages/{package_id}", response_model=HostingPackageOut)
def update_hosting_package(
    package_id: int,
    payload: HostingPackageUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    package = get_package_or_404(db, package_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return package

    if "name" in updates:
        existing = db.query(HostingPackage).filter(HostingPackage.name == updates["name"], HostingPackage.id != package.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Hosting package name already exists.")
    if "whm_package_id" in updates:
        existing = db.query(HostingPackage).filter(
            HostingPackage.whm_package_id == updates["whm_package_id"],
            HostingPackage.id != package.id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="WHM package mapping already exists.")

    changes = []
    for field, value in updates.items():
        old_value = getattr(package, field)
        if old_value != value:
            changes.append(f"{field}: {old_value} -> {value}")
            setattr(package, field, value)

    if changes:
        write_audit_log(
            db,
            "admin.hosting_package.update",
            admin.id,
            "hosting_package",
            str(package.id),
            "; ".join(changes),
        )
    db.commit()
    db.refresh(package)
    return package

@router.put("/hosting-packages/{package_id}/disable", response_model=HostingPackageOut)
def disable_hosting_package(
    package_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    package = get_package_or_404(db, package_id)
    old_status = package.is_active
    package.is_active = False
    write_audit_log(
        db,
        "admin.hosting_package.disable",
        admin.id,
        "hosting_package",
        str(package.id),
        f"is_active: {old_status} -> {package.is_active}",
    )
    db.commit()
    db.refresh(package)
    return package

@router.delete("/hosting-packages/{package_id}")
def delete_hosting_package(
    package_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    package = get_package_or_404(db, package_id)
    linked_orders = db.query(HostingOrder).filter(HostingOrder.package_id == package.id).count()
    if linked_orders:
        raise HTTPException(status_code=400, detail="Cannot delete a package with linked hosting orders.")

    package_name = package.name
    db.delete(package)
    write_audit_log(
        db,
        "admin.hosting_package.delete",
        admin.id,
        "hosting_package",
        str(package_id),
        f"Deleted unused package {package_name}.",
    )
    db.commit()
    return {"status": "deleted"}

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
    return get_order_or_404(db, order_id)

@router.post("/hosting/{order_id}/retry-provisioning", response_model=HostingOrderOut)
def retry_failed_provisioning(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    order = get_order_or_404(db, order_id)
    if order.status != HostingStatus.PROVISION_FAILED:
        raise HTTPException(status_code=400, detail="Only failed provisioning orders can be retried.")

    old_status = order.status
    order.status = HostingStatus.PROVISIONING
    order.provision_error = None
    write_audit_log(
        db,
        "admin.hosting.retry_provisioning",
        admin.id,
        "hosting_order",
        str(order.id),
        f"status: {old_status} -> {order.status}",
    )
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

@router.post("/hosting/{order_id}/suspend", response_model=HostingOrderOut)
async def suspend_hosting_order(
    order_id: int,
    payload: HostingSuspendRequest,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    username = require_cpanel_username(order)
    result = await whm_service.suspend_account(username, payload.reason)
    ensure_provider_success(result, "Suspend hosting")

    old_status = order.status
    order.status = HostingStatus.SUSPENDED
    write_audit_log(
        db,
        "admin.hosting.suspend",
        admin.id,
        "hosting_order",
        str(order.id),
        f"status: {old_status} -> {order.status}; reason: {payload.reason}",
    )
    db.commit()
    db.refresh(order)
    return order

@router.post("/hosting/{order_id}/unsuspend", response_model=HostingOrderOut)
async def unsuspend_hosting_order(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    username = require_cpanel_username(order)
    result = await whm_service.unsuspend_account(username)
    ensure_provider_success(result, "Unsuspend hosting")

    old_status = order.status
    order.status = HostingStatus.ACTIVE
    write_audit_log(
        db,
        "admin.hosting.unsuspend",
        admin.id,
        "hosting_order",
        str(order.id),
        f"status: {old_status} -> {order.status}",
    )
    db.commit()
    db.refresh(order)
    return order

@router.post("/hosting/{order_id}/terminate", response_model=HostingOrderOut)
async def terminate_hosting_order(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    username = require_cpanel_username(order)
    result = await whm_service.terminate_account(username)
    ensure_provider_success(result, "Terminate hosting")

    old_status = order.status
    order.status = HostingStatus.TERMINATED
    write_audit_log(
        db,
        "admin.hosting.terminate",
        admin.id,
        "hosting_order",
        str(order.id),
        f"status: {old_status} -> {order.status}",
    )
    db.commit()
    db.refresh(order)
    return order

@router.post("/hosting/{order_id}/reset-password")
async def reset_hosting_password(
    order_id: int,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    username = require_cpanel_username(order)
    result = await whm_service.reset_password(username)
    ensure_provider_success(result, "Reset hosting password")

    write_audit_log(
        db,
        "admin.hosting.reset_password",
        admin.id,
        "hosting_order",
        str(order.id),
        "cPanel password reset through provider boundary.",
    )
    db.commit()
    return result

@router.post("/hosting/{order_id}/change-package", response_model=HostingOrderOut)
async def change_hosting_package(
    order_id: int,
    payload: HostingChangePackageRequest,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    package = get_package_or_404(db, payload.package_id)
    if not package.is_active:
        raise HTTPException(status_code=400, detail="Cannot change to an inactive hosting package.")
    username = require_cpanel_username(order)
    result = await whm_service.change_package(username, package.whm_package_id)
    ensure_provider_success(result, "Change hosting package")

    old_package = order.package_name
    old_whm_package_id = order.whm_package_id
    order.package_id = package.id
    order.package_name = package.name
    order.whm_package_id = package.whm_package_id
    write_audit_log(
        db,
        "admin.hosting.change_package",
        admin.id,
        "hosting_order",
        str(order.id),
        f"package: {old_package}/{old_whm_package_id} -> {package.name}/{package.whm_package_id}",
    )
    db.commit()
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
    old_status = invoice.status
    invoice.status = payload.status
    if payload.status == InvoiceStatus.PAID and not invoice.paid_at:
        invoice.paid_at = datetime.utcnow()
    if payload.status != InvoiceStatus.PAID:
        invoice.paid_at = None
    write_audit_log(
        db,
        "admin.invoice.status_update",
        admin.id,
        "invoice",
        str(invoice.id),
        f"status: {old_status} -> {invoice.status}",
    )
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
    return get_domain_or_404(db, domain_id)

@router.put("/domains/{domain_id}/status", response_model=DomainOrderOut)
def update_domain_status(
    domain_id: int,
    payload: DomainStatusUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    domain = get_domain_or_404(db, domain_id)
    old_status = domain.status
    domain.status = payload.status
    write_audit_log(
        db,
        "admin.domain.status_update",
        admin.id,
        "domain",
        str(domain.id),
        f"status: {old_status} -> {domain.status}",
    )
    db.commit()
    db.refresh(domain)
    return domain

@router.put("/domains/{domain_id}/nameservers", response_model=DomainOrderOut)
async def update_domain_nameservers(
    domain_id: int,
    payload: DomainNameserverUpdate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    domain = get_domain_or_404(db, domain_id)
    result = await domain_provider.update_nameservers(domain.domain_name, [payload.ns1, payload.ns2])
    ensure_provider_success(result, "Update domain nameservers")

    old_ns = f"{domain.ns1}, {domain.ns2}"
    domain.ns1 = payload.ns1
    domain.ns2 = payload.ns2
    write_audit_log(
        db,
        "admin.domain.nameservers_update",
        admin.id,
        "domain",
        str(domain.id),
        f"nameservers: {old_ns} -> {domain.ns1}, {domain.ns2}",
    )
    db.commit()
    db.refresh(domain)
    return domain

@router.post("/domains/{domain_id}/renew", response_model=DomainOrderOut)
async def renew_domain(
    domain_id: int,
    payload: DomainRenewRequest,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    domain = get_domain_or_404(db, domain_id)
    result = await domain_provider.renew_domain(domain.domain_name, payload.years)
    ensure_provider_success(result, "Renew domain")

    old_expiry = domain.expiry_date
    baseline = domain.expiry_date
    now = datetime.utcnow()
    if baseline is None or baseline.replace(tzinfo=None) < now:
        baseline = now
    domain.expiry_date = baseline + timedelta(days=365 * payload.years)
    write_audit_log(
        db,
        "admin.domain.renew",
        admin.id,
        "domain",
        str(domain.id),
        f"expiry_date: {old_expiry} -> {domain.expiry_date}; years: {payload.years}",
    )
    db.commit()
    db.refresh(domain)
    return domain

@router.put("/hosting/{order_id}/toggle-status", response_model=HostingOrderOut)
def administrative_hosting_status_override(
    order_id: int,
    payload: HostingStatusOverride,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    Emergency override for manual hosting status changes when provider workflows cannot be used.
    """
    order = get_order_or_404(db, order_id)
    old_status = order.status
    order.status = payload.status
    write_audit_log(
        db,
        "admin.hosting.status_override",
        admin.id,
        "hosting_order",
        str(order.id),
        f"status: {old_status} -> {order.status}",
    )
    db.commit()
    db.refresh(order)
    return order
