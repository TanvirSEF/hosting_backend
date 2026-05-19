# app/api/v1/backups.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import BackupJob, BackupStatus
from app.schemas.hosting_tools import BackupCreate, BackupJobOut
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action
from app.tasks.hosting_tool_tasks import restore_backup_mock, run_backup_mock

router = APIRouter()


@router.get("/{hosting_order_id}", response_model=List[BackupJobOut])
def list_backups(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(BackupJob).filter(BackupJob.hosting_order_id == hosting_order_id).order_by(BackupJob.id.desc()).all()


@router.post("/{hosting_order_id}", response_model=BackupJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_backup(
    hosting_order_id: int,
    payload: BackupCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    backup = BackupJob(hosting_order_id=hosting_order_id, backup_type=payload.backup_type, status=BackupStatus.QUEUED)
    db.add(backup)
    db.flush()
    log_tool_action(db, hosting_order_id, "backup", "queue_create", "queued", "Simulated backup queued.")
    try:
        run_backup_mock.delay(backup.id)
    except Exception as exc:
        backup.status = BackupStatus.FAILED
        backup.message = f"Failed to queue backup: {exc}"
    db.commit()
    db.refresh(backup)
    return backup


@router.post("/{backup_id}/restore", response_model=BackupJobOut, status_code=status.HTTP_202_ACCEPTED)
def restore_backup(backup_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    backup = db.query(BackupJob).filter(BackupJob.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup job not found.")
    get_owned_hosting_order(db, backup.hosting_order_id, user_id)
    backup.status = BackupStatus.RESTORING
    backup.message = "Simulated restore queued."
    log_tool_action(db, backup.hosting_order_id, "backup", "queue_restore", "queued", "Simulated backup restore queued.")
    try:
        restore_backup_mock.delay(backup.id)
    except Exception as exc:
        backup.status = BackupStatus.FAILED
        backup.message = f"Failed to queue restore: {exc}"
    db.commit()
    db.refresh(backup)
    return backup
