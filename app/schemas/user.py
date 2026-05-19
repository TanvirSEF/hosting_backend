# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Signup req payload wrapper
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)

# Login req payload wrapper
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

# Outbound serialization interface (Hiding hashes)
class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Session return schema token context mapping
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: UserOut
