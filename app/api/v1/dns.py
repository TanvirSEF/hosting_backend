# app/api/v1/dns.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import DnsRecord
from app.schemas.hosting_tools import DnsRecordCreate, DnsRecordOut, DnsRecordUpdate
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action

router = APIRouter()


@router.get("/{hosting_order_id}/records", response_model=List[DnsRecordOut])
def list_dns_records(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(DnsRecord).filter(DnsRecord.hosting_order_id == hosting_order_id).all()


@router.post("/{hosting_order_id}/records", response_model=DnsRecordOut, status_code=status.HTTP_201_CREATED)
def create_dns_record(
    hosting_order_id: int,
    payload: DnsRecordCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    record = DnsRecord(hosting_order_id=hosting_order_id, **payload.model_dump())
    db.add(record)
    log_tool_action(db, hosting_order_id, "dns", "create_record")
    db.commit()
    db.refresh(record)
    return record


@router.put("/records/{record_id}", response_model=DnsRecordOut)
def update_dns_record(
    record_id: int,
    payload: DnsRecordUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    record = db.query(DnsRecord).filter(DnsRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="DNS record not found.")
    get_owned_hosting_order(db, record.hosting_order_id, user_id)
    for key, value in payload.model_dump().items():
        setattr(record, key, value)
    log_tool_action(db, record.hosting_order_id, "dns", "update_record")
    db.commit()
    db.refresh(record)
    return record


@router.delete("/records/{record_id}")
def delete_dns_record(record_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    record = db.query(DnsRecord).filter(DnsRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="DNS record not found.")
    get_owned_hosting_order(db, record.hosting_order_id, user_id)
    hosting_order_id = record.hosting_order_id
    db.delete(record)
    log_tool_action(db, hosting_order_id, "dns", "delete_record")
    db.commit()
    return {"status": "deleted"}
