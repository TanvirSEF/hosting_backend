# app/api/v1/databases.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import HostingDatabase
from app.schemas.hosting_tools import HostingDatabaseCreate, HostingDatabaseOut
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action

router = APIRouter()


@router.get("/{hosting_order_id}", response_model=List[HostingDatabaseOut])
def list_databases(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(HostingDatabase).filter(HostingDatabase.hosting_order_id == hosting_order_id).all()


@router.post("/{hosting_order_id}", response_model=HostingDatabaseOut, status_code=status.HTTP_201_CREATED)
def create_database(
    hosting_order_id: int,
    payload: HostingDatabaseCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    existing = (
        db.query(HostingDatabase)
        .filter(HostingDatabase.hosting_order_id == hosting_order_id, HostingDatabase.database_name == payload.database_name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Database already exists for this hosting order.")
    database = HostingDatabase(
        hosting_order_id=hosting_order_id,
        database_name=payload.database_name,
        username=payload.username,
        status="active",
    )
    db.add(database)
    log_tool_action(db, hosting_order_id, "database", "create_database")
    db.commit()
    db.refresh(database)
    return database


@router.delete("/{database_id}")
def delete_database(database_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    database = db.query(HostingDatabase).filter(HostingDatabase.id == database_id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found.")
    get_owned_hosting_order(db, database.hosting_order_id, user_id)
    hosting_order_id = database.hosting_order_id
    db.delete(database)
    log_tool_action(db, hosting_order_id, "database", "delete_database")
    db.commit()
    return {"status": "deleted"}
