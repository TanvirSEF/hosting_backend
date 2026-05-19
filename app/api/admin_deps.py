# app/api/admin_deps.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.api.deps import get_current_user_id

def require_admin_user(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency guard that intercepts incoming requests, extracts the subject user,
    and raises an unauthorized exception if the user is not a system administrator.
    """
    # Fetch user data from PostgreSQL database relation
    user = db.query(User).filter(User.id == current_user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Authenticated user record no longer exists."
        )
        
    # Verify strict role status flag matching product requirements
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrative privileges required."
        )
        
    return user# app/api/admin_deps.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.api.deps import get_current_user_id

def require_admin_user(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency guard that intercepts incoming requests, extracts the subject user,
    and raises an unauthorized exception if the user is not a system administrator.
    """
    # Fetch user data from PostgreSQL database relation
    user = db.query(User).filter(User.id == current_user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Authenticated user record no longer exists."
        )
        
    # Verify strict role status flag matching product requirements
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrative privileges required."
        )
        
    return user