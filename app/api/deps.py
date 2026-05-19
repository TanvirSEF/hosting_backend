# app/api/deps.py
from datetime import datetime
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
import jwt
from app.core.config import settings
from app.database.session import get_db
from app.models.security import TokenBlacklist
from app.models.user import User

def decode_bearer_token(
    authorization: str,
    db: Session,
    expected_type: str = "access",
) -> dict:
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token format. Use Bearer <token>")

        token = authorization.split(" ")[1]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type", "access") != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token type.")
        jti = payload.get("jti")
        if jti:
            blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
            if blacklisted:
                raise HTTPException(status_code=401, detail="Token has been revoked.")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")

def get_current_user_id(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> int:
    try:
        payload = decode_bearer_token(authorization, db, "access")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing user information.")
        return int(user_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")

def get_current_user(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Authenticated user record no longer exists.")
    return user
