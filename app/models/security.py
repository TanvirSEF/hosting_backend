# app/models/security.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func
from app.database.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminTwoFactorSetting(Base):
    __tablename__ = "admin_two_factor_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    method = Column(String, default="placeholder")
    secret_hint = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, unique=True, index=True, nullable=False)
    credential_type = Column(String, nullable=False)
    encrypted_secret = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
