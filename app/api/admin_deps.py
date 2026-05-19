# app/api/admin_deps.py
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.api.deps import get_current_user

def require_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency guard that intercepts incoming requests, extracts the subject user,
    and raises an unauthorized exception if the user is not a system administrator.
    """
    # Verify strict role status flag matching product requirements
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrative privileges required."
        )
        
    return user
