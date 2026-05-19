# app/api/v1/whmcs.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.admin_deps import require_admin_user
from app.database.session import get_db
from app.models.user import User
from app.models.whmcs import WhmcsImportBatch, WhmcsImportRow
from app.schemas.whmcs import WhmcsImportBatchCreate, WhmcsImportBatchDetail, WhmcsImportBatchOut

router = APIRouter()


def batch_detail(db: Session, batch: WhmcsImportBatch) -> dict:
    rows = db.query(WhmcsImportRow).filter(WhmcsImportRow.batch_id == batch.id).order_by(WhmcsImportRow.id.asc()).all()
    return {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "created_by_user_id": batch.created_by_user_id,
        "created_at": batch.created_at,
        "processed_at": batch.processed_at,
        "rows": rows,
    }


@router.post("/import-batches", response_model=WhmcsImportBatchDetail, status_code=status.HTTP_201_CREATED)
def create_import_batch(
    payload: WhmcsImportBatchCreate,
    admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    batch = WhmcsImportBatch(name=payload.name, created_by_user_id=admin.id, status="draft")
    db.add(batch)
    db.flush()
    for row in payload.rows:
        db.add(
            WhmcsImportRow(
                batch_id=batch.id,
                row_type=row.row_type,
                source_id=row.source_id,
                payload=row.payload,
                status="pending",
            )
        )
    db.commit()
    db.refresh(batch)
    return batch_detail(db, batch)


@router.get("/import-batches", response_model=List[WhmcsImportBatchOut])
def list_import_batches(admin: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    return db.query(WhmcsImportBatch).order_by(WhmcsImportBatch.id.desc()).all()


@router.get("/import-batches/{batch_id}", response_model=WhmcsImportBatchDetail)
def get_import_batch(batch_id: int, admin: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    batch = db.query(WhmcsImportBatch).filter(WhmcsImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="WHMCS import batch not found.")
    return batch_detail(db, batch)


@router.post("/import-batches/{batch_id}/process", response_model=WhmcsImportBatchDetail)
def process_import_batch(batch_id: int, admin: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    batch = db.query(WhmcsImportBatch).filter(WhmcsImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="WHMCS import batch not found.")

    supported = {"user", "hosting_service", "domain", "invoice"}
    rows = db.query(WhmcsImportRow).filter(WhmcsImportRow.batch_id == batch.id).all()
    for row in rows:
        if row.row_type not in supported:
            row.status = "skipped"
            row.message = "Unsupported row type."
        elif not row.payload:
            row.status = "failed"
            row.message = "Missing row payload."
        else:
            row.status = "ready"
            row.message = "Validated for future non-destructive import."

    batch.status = "processed"
    batch.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch_detail(db, batch)
