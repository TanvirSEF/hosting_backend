# app/api/v1/wordpress.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.hosting_tools import WordPressInstall, WordPressStatus
from app.schemas.hosting_tools import WordPressInstallCreate, WordPressInstallOut
from app.services.hosting_tools import get_owned_hosting_order, log_tool_action
from app.tasks.hosting_tool_tasks import install_wordpress_mock

router = APIRouter()


@router.get("/{hosting_order_id}", response_model=List[WordPressInstallOut])
def list_wordpress_installs(hosting_order_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    return db.query(WordPressInstall).filter(WordPressInstall.hosting_order_id == hosting_order_id).all()


@router.post("/{hosting_order_id}/install", response_model=WordPressInstallOut, status_code=status.HTTP_202_ACCEPTED)
def install_wordpress(
    hosting_order_id: int,
    payload: WordPressInstallCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_owned_hosting_order(db, hosting_order_id, user_id)
    install = WordPressInstall(
        hosting_order_id=hosting_order_id,
        site_url=payload.site_url,
        admin_username=payload.admin_username,
        status=WordPressStatus.PENDING,
    )
    db.add(install)
    db.flush()
    log_tool_action(db, hosting_order_id, "wordpress", "queue_install", "queued", "Simulated WordPress install queued.")
    try:
        install_wordpress_mock.delay(install.id)
    except Exception as exc:
        install.status = WordPressStatus.FAILED
        install.install_error = f"Failed to queue WordPress install: {exc}"
    db.commit()
    db.refresh(install)
    return install
