# app/api/v1/ssl.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import SslCertificate, SslStatus
from app.schemas.hosting_tools import SslCertificateOut
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action

router = APIRouter()


def get_or_create_certificate(db: Session, hosting_order_id: int, domain: str) -> SslCertificate:
    cert = db.query(SslCertificate).filter(SslCertificate.hosting_order_id == hosting_order_id).first()
    if cert:
        return cert
    cert = SslCertificate(hosting_order_id=hosting_order_id, domain=domain, status=SslStatus.NOT_ISSUED)
    db.add(cert)
    db.flush()
    return cert


@router.get("/{hosting_order_id}", response_model=SslCertificateOut)
def get_ssl_certificate(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    order = get_owned_hosting_order(db, hosting_order_id, user_id)
    cert = get_or_create_certificate(db, hosting_order_id, order.domain)
    db.commit()
    db.refresh(cert)
    return cert


@router.post("/{hosting_order_id}/issue", response_model=SslCertificateOut)
def issue_ssl_certificate(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    order = get_owned_hosting_order(db, hosting_order_id, user_id)
    cert = get_or_create_certificate(db, hosting_order_id, order.domain)
    cert.status = SslStatus.ACTIVE
    cert.issuer = "Simulated NexHost AutoSSL"
    cert.issued_at = datetime.utcnow()
    cert.expires_at = datetime.utcnow() + timedelta(days=90)
    log_tool_action(db, hosting_order_id, "ssl", "issue")
    db.commit()
    db.refresh(cert)
    return cert


@router.post("/{hosting_order_id}/renew", response_model=SslCertificateOut)
def renew_ssl_certificate(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    order = get_owned_hosting_order(db, hosting_order_id, user_id)
    cert = get_or_create_certificate(db, hosting_order_id, order.domain)
    cert.status = SslStatus.ACTIVE
    cert.issuer = "Simulated NexHost AutoSSL"
    cert.issued_at = datetime.utcnow()
    cert.expires_at = datetime.utcnow() + timedelta(days=90)
    log_tool_action(db, hosting_order_id, "ssl", "renew")
    db.commit()
    db.refresh(cert)
    return cert
