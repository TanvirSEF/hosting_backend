# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Signup req payload wrapper
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

# Login req payload wrapper
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Outbound serialization interface (Hiding hashes)
class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Session return schema token context mapping
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut