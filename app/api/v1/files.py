# app/api/v1/files.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import FileManagerEntry
from app.schemas.hosting_tools import FileManagerEntryOut, FileMetadataCreate, FolderCreate
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action

router = APIRouter()


def build_path(db: Session, hosting_order_id: int, parent_id: int | None, name: str) -> str:
    if parent_id is None:
        return f"/{name}"
    parent = (
        db.query(FileManagerEntry)
        .filter(FileManagerEntry.id == parent_id, FileManagerEntry.hosting_order_id == hosting_order_id)
        .first()
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent folder not found.")
    return f"{parent.path.rstrip('/')}/{name}"


@router.get("/{hosting_order_id}", response_model=List[FileManagerEntryOut])
def list_file_entries(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(FileManagerEntry).filter(FileManagerEntry.hosting_order_id == hosting_order_id).all()


@router.post("/{hosting_order_id}/folders", response_model=FileManagerEntryOut, status_code=status.HTTP_201_CREATED)
def create_folder(
    hosting_order_id: int,
    payload: FolderCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    entry = FileManagerEntry(
        hosting_order_id=hosting_order_id,
        parent_id=payload.parent_id,
        name=payload.name,
        path=build_path(db, hosting_order_id, payload.parent_id, payload.name),
        entry_type="folder",
        size_bytes=0,
    )
    db.add(entry)
    log_tool_action(db, hosting_order_id, "file_manager", "create_folder")
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{hosting_order_id}/upload-metadata", response_model=FileManagerEntryOut, status_code=status.HTTP_201_CREATED)
def upload_file_metadata(
    hosting_order_id: int,
    payload: FileMetadataCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    entry = FileManagerEntry(
        hosting_order_id=hosting_order_id,
        parent_id=payload.parent_id,
        name=payload.name,
        path=build_path(db, hosting_order_id, payload.parent_id, payload.name),
        entry_type="file",
        size_bytes=payload.size_bytes,
    )
    db.add(entry)
    log_tool_action(db, hosting_order_id, "file_manager", "upload_metadata")
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}")
def delete_file_entry(entry_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    entry = db.query(FileManagerEntry).filter(FileManagerEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="File manager entry not found.")
    get_owned_hosting_order(db, entry.hosting_order_id, user_id)
    hosting_order_id = entry.hosting_order_id
    db.delete(entry)
    log_tool_action(db, hosting_order_id, "file_manager", "delete_entry")
    db.commit()
    return {"status": "deleted"}
