# app/api/v1/usage.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import HostingUsageSnapshot
from app.schemas.hosting_tools import UsageSnapshotOut
from app.services.hosting_tools import get_owned_hosting_order

router = APIRouter()


@router.get("/{hosting_order_id}", response_model=List[UsageSnapshotOut])
def list_usage_snapshots(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return (
        db.query(HostingUsageSnapshot)
        .filter(HostingUsageSnapshot.hosting_order_id == hosting_order_id)
        .order_by(HostingUsageSnapshot.id.desc())
        .all()
    )
