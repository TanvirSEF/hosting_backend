# app/api/v1/hosting.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.hosting import HostingOrder, HostingStatus
from app.schemas.hosting import HostingCreateRequest, HostingOrderOut
from app.api.deps import get_current_user_id  # সিকিউর গার্ড ইমপোর্ট
from app.services.whm import whm_service

router = APIRouter()

@router.post("/provision", response_model=HostingOrderOut, status_code=status.HTTP_201_CREATED)
async def provision_hosting(
    payload: HostingCreateRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    
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

    whm_result = await whm_service.create_cpanel_account(
        domain=payload.domain,
        plan_package=payload.package_name,
        contact_email="automated-system@nexhost.com"
    )

    if whm_result.get("success"):
        new_order.username = whm_result.get("username")
        new_order.status = HostingStatus.ACTIVE
        db.commit()
        db.refresh(new_order)
        return new_order
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"WHM automated provisioning error: {whm_result.get('error')}"
        )

@router.get("/my-services", response_model=List[HostingOrderOut])
def get_user_services(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    services = db.query(HostingOrder).filter(HostingOrder.user_id == user_id).all()
    return services