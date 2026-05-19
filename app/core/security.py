# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Union
from uuid import uuid4
from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Bcrypt instance mapping configuration context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Plain string-ke secure crypt hash string-e convert korbe"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Incoming plain payload context pass-db match checking execution"""
    return pwd_context.verify(plain_password, hashed_password)

def create_token(subject: Union[str, Any], token_type: str, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
        "jti": str(uuid4()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        delta = expires_delta
    else:
        delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(subject, "access", delta)

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        delta = expires_delta
    else:
        delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(subject, "refresh", delta)
