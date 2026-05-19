# app/api/v1/hosting.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.hosting import HostingOrder, HostingStatus
from app.schemas.hosting import HostingCreateRequest, HostingOrderOut
from app.api.deps import get_current_user_id
from app.tasks.hosting_tasks import provision_cpanel_async # Import the task queue handle

router = APIRouter()

@router.post("/provision", response_model=HostingOrderOut, status_code=status.HTTP_202_ACCEPTED)
async def provision_hosting(
    payload: HostingCreateRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Refactored endpoint that processes instantly and passes long running operations
    directly into our safe Redis + Celery job manager queue schema.
    """
    # 1. Immediately log order entry in database under PENDING state
    new_order = HostingOrder(
        user_id=user_id,
        domain=payload.domain,
        package_name=payload.package_name,
        status=HostingStatus.PENDING,
        whm_package_id=payload.package_name
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 2. Push task parameters directly onto the broker pipeline queue
    provision_cpanel_async.delay(new_order.id, "automated-client@nexhost.com")

    # 3. Return immediate response back to client dashboard layout framework wrapper
    return new_order

@router.get("/my-services", response_model=List[HostingOrderOut])
def get_user_services(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Returns array containing services owned by current active session client context."""
    services = db.query(HostingOrder).filter(HostingOrder.user_id == user_id).all()
    return services