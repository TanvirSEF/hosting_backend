# app/api/v1/domain.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database.session import get_db
from app.models.domain import UserDomain, DomainStatus
from app.schemas.domain import DomainSearchRequest, DomainRegisterRequest, DomainOrderOut
from app.api.deps import get_current_user_id
from app.services.domain_provider import domain_provider

router = APIRouter()

@router.post("/search")
async def search_domain(payload: DomainSearchRequest):
    """
    Public endpoint for searching domain availability from the customer platform front page.
    """
    result = await domain_provider.check_availability(payload.domain_name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail="External registrar API query failure.")
    return result

@router.post("/register", response_model=DomainOrderOut, status_code=status.HTTP_201_CREATED)
async def register_domain(
    payload: DomainRegisterRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Authenticated action tracking domain orders inside client database layer after successful billing checkpoint.
    """
    # 1. Ensure domain isn't already registered within internal systems locally
    existing_domain = db.query(UserDomain).filter(UserDomain.domain_name == payload.domain_name).first()
    if existing_domain:
        raise HTTPException(status_code=400, detail="This domain is already mapped inside NexHost systems.")

    # 2. Trigger simulation mapping to third-party adapter execution infrastructure
    reg_result = await domain_provider.register_domain_infrastructure(payload.domain_name, payload.years)
    
    if not reg_result.get("success"):
        raise HTTPException(status_code=500, detail="Registrar gateway provisioning error.")

    # 3. Calculate lifecycle metrics (e.g., Expiration date calculation based on leased years parameter)
    expiry_date_calc = datetime.utcnow() + timedelta(days=365 * payload.years)

    # 4. Save structural baseline data points directly into PostgreSQL database safely
    new_domain = UserDomain(
        user_id=user_id,
        domain_name=payload.domain_name,
        status=DomainStatus.ACTIVE,
        expiry_date=expiry_date_calc
    )
    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)
    return new_domain

@router.get("/my-domains", response_model=List[DomainOrderOut])
def list_user_domains(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Returns array containing domain lifecycle records owned by authenticated context user.
    """
    domains = db.query(UserDomain).filter(UserDomain.user_id == user_id).all()
    return domains