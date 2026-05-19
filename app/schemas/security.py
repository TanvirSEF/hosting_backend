from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class TwoFactorSetupOut(BaseModel):
    enabled: bool
    method: str
    secret_hint: str
    message: str


class TwoFactorUpdateRequest(BaseModel):
    code: str


class ProviderCredentialCreate(BaseModel):
    provider_name: str
    credential_type: str
    secret: str


class ProviderCredentialOut(BaseModel):
    id: int
    provider_name: str
    credential_type: str
    is_active: bool
    created_by_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
