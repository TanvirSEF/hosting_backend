# app/api/deps.py
from fastapi import Header, HTTPException, Depends
import jwt
from app.core.config import settings

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