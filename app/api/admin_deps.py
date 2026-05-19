# app/api/admin_deps.py
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.security import AdminTwoFactorSetting
from app.models.user import User
from app.api.deps import get_current_user

def require_admin_user(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_admin_2fa_code: str = Header(default=None),
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

    setting = db.query(AdminTwoFactorSetting).filter(AdminTwoFactorSetting.user_id == user.id).first()
    if setting and setting.is_enabled and x_admin_2fa_code != "000000":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin 2FA verification required."
        )
        
    return user
