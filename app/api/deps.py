# app/api/deps.py
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
import jwt
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User

def get_current_user_id(authorization: str = Header(...)) -> int:
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token format. Use Bearer <token>")
        
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing user information.")
        return int(user_id)
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
