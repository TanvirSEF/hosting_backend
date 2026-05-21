from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.billing import BillingReason, BillingServiceType, Invoice, InvoiceStatus
from app.models.domain import DomainStatus, UserDomain
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.services.audit import write_audit_log


DEFAULT_DOMAIN_RENEWAL_PRICE_BDT = Decimal("1200.00")


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=None)


def _existing_unpaid_renewal_invoice(
    db: Session,
    service_type: BillingServiceType,
    service_id: int,
) -> Invoice | None:
    return (
        db.query(Invoice)
        .filter(
            Invoice.service_type == service_type,
            Invoice.service_id == service_id,
            Invoice.billing_reason == BillingReason.RENEWAL,
            Invoice.status == InvoiceStatus.UNPAID,
        )
        .first()
    )


def create_hosting_renewal_invoice(
    db: Session,
    order: HostingOrder,
    days_valid: int = 7,
) -> Invoice:
    existing = _existing_unpaid_renewal_invoice(db, BillingServiceType.HOSTING, order.id)
    if existing:
        return existing

    package = db.query(HostingPackage).filter(HostingPackage.id == order.package_id).first()
    if not package:
        raise ValueError("Hosting package is missing; cannot calculate renewal invoice.")

    invoice = Invoice(
        user_id=order.user_id,
        amount=package.price_bdt,
        status=InvoiceStatus.UNPAID,
        service_type=BillingServiceType.HOSTING,
        service_id=order.id,
        billing_reason=BillingReason.RENEWAL,
        due_at=datetime.utcnow() + timedelta(days=days_valid),
    )
    db.add(invoice)
    db.flush()
    write_audit_log(
        db,
        "billing.hosting_renewal_invoice.create",
        None,
        "hosting_order",
        str(order.id),
        f"Created renewal invoice #{invoice.id}.",
    )
    return invoice


def create_domain_renewal_invoice(
    db: Session,
    domain: UserDomain,
    days_valid: int = 7,
) -> Invoice:
    existing = _existing_unpaid_renewal_invoice(db, BillingServiceType.DOMAIN, domain.id)
    if existing:
        return existing

    invoice = Invoice(
        user_id=domain.user_id,
        amount=DEFAULT_DOMAIN_RENEWAL_PRICE_BDT,
        status=InvoiceStatus.UNPAID,
        service_type=BillingServiceType.DOMAIN,
        service_id=domain.id,
        billing_reason=BillingReason.RENEWAL,
        due_at=datetime.utcnow() + timedelta(days=days_valid),
    )
    db.add(invoice)
    db.flush()
    write_audit_log(
        db,
        "billing.domain_renewal_invoice.create",
        None,
        "domain",
        str(domain.id),
        f"Created renewal invoice #{invoice.id}.",
    )
    return invoice


def generate_renewal_invoices(db: Session, days_ahead: int = 7) -> dict:
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)
    hosting_count = 0
    domain_count = 0

    hosting_orders = (
        db.query(HostingOrder)
        .filter(
            HostingOrder.auto_renew == True,
            HostingOrder.expires_at != None,
            HostingOrder.expires_at <= cutoff,
            HostingOrder.status.in_([HostingStatus.ACTIVE, HostingStatus.SUSPENDED]),
        )
        .all()
    )
    for order in hosting_orders:
        if not _existing_unpaid_renewal_invoice(db, BillingServiceType.HOSTING, order.id):
            create_hosting_renewal_invoice(db, order)
            hosting_count += 1

    domains = (
        db.query(UserDomain)
        .filter(
            UserDomain.auto_renew == True,
            UserDomain.expiry_date <= cutoff,
            UserDomain.status == DomainStatus.ACTIVE,
        )
        .all()
    )
    for domain in domains:
        if not _existing_unpaid_renewal_invoice(db, BillingServiceType.DOMAIN, domain.id):
            create_domain_renewal_invoice(db, domain)
            domain_count += 1

    return {
        "generated_hosting_invoices": hosting_count,
        "generated_domain_invoices": domain_count,
    }


def mark_due_reminders(db: Session, days_ahead: int = 3) -> int:
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.status == InvoiceStatus.UNPAID,
            Invoice.due_at <= cutoff,
            Invoice.reminder_sent_at == None,
        )
        .all()
    )
    for invoice in invoices:
        invoice.reminder_sent_at = datetime.utcnow()
        write_audit_log(
            db,
            "billing.invoice.reminder_marked",
            None,
            "invoice",
            str(invoice.id),
            "Due reminder marked for notification delivery.",
        )
    return len(invoices)


def apply_paid_invoice_lifecycle(db: Session, invoice: Invoice) -> dict:
    if invoice.billing_reason != BillingReason.RENEWAL or not invoice.service_type or not invoice.service_id:
        return {"applied": False}

    if invoice.service_type == BillingServiceType.HOSTING:
        order = db.query(HostingOrder).filter(HostingOrder.id == invoice.service_id).first()
        if not order:
            return {"applied": False, "reason": "hosting_order_not_found"}
        package = db.query(HostingPackage).filter(HostingPackage.id == order.package_id).first()
        period_days = package.billing_period_days if package else 30
        baseline = _naive_utc(order.expires_at)
        now = datetime.utcnow()
        if baseline is None or baseline < now:
            baseline = now
        old_expiry = order.expires_at
        order.expires_at = baseline + timedelta(days=period_days)
        if order.status == HostingStatus.SUSPENDED:
            order.status = HostingStatus.ACTIVE
        write_audit_log(
            db,
            "billing.hosting_renewal.apply",
            None,
            "hosting_order",
            str(order.id),
            f"expiry: {old_expiry} -> {order.expires_at}",
        )
        return {"applied": True, "service_type": "hosting", "service_id": order.id}

    if invoice.service_type == BillingServiceType.DOMAIN:
        domain = db.query(UserDomain).filter(UserDomain.id == invoice.service_id).first()
        if not domain:
            return {"applied": False, "reason": "domain_not_found"}
        baseline = _naive_utc(domain.expiry_date)
        now = datetime.utcnow()
        if baseline is None or baseline < now:
            baseline = now
        old_expiry = domain.expiry_date
        domain.expiry_date = baseline + timedelta(days=365)
        domain.status = DomainStatus.ACTIVE
        write_audit_log(
            db,
            "billing.domain_renewal.apply",
            None,
            "domain",
            str(domain.id),
            f"expiry: {old_expiry} -> {domain.expiry_date}",
        )
        return {"applied": True, "service_type": "domain", "service_id": domain.id}

    return {"applied": False}


def process_overdue_services(db: Session) -> dict:
    now = datetime.utcnow()
    hosting_suspended = 0
    domains_expired = 0

    overdue_hosting_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.status == InvoiceStatus.UNPAID,
            Invoice.billing_reason == BillingReason.RENEWAL,
            Invoice.service_type == BillingServiceType.HOSTING,
            Invoice.due_at < now,
            Invoice.overdue_processed_at == None,
        )
        .all()
    )
    for invoice in overdue_hosting_invoices:
        order = db.query(HostingOrder).filter(HostingOrder.id == invoice.service_id).first()
        if order and order.status == HostingStatus.ACTIVE:
            order.status = HostingStatus.SUSPENDED
            hosting_suspended += 1
            write_audit_log(
                db,
                "billing.hosting_overdue.suspend",
                None,
                "hosting_order",
                str(order.id),
                f"Suspended for overdue invoice #{invoice.id}.",
            )
        invoice.overdue_processed_at = now

    expired_domains = (
        db.query(UserDomain)
        .filter(UserDomain.expiry_date < now, UserDomain.status == DomainStatus.ACTIVE)
        .all()
    )
    for domain in expired_domains:
        domain.status = DomainStatus.EXPIRED
        domains_expired += 1
        write_audit_log(
            db,
            "billing.domain_expired.mark",
            None,
            "domain",
            str(domain.id),
            "Domain marked expired by lifecycle job.",
        )

    return {
        "hosting_suspended": hosting_suspended,
        "domains_expired": domains_expired,
    }
