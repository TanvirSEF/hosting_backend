# app/models/hosting_tools.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from app.database.session import Base
import enum


class ToolActionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DnsRecordType(str, enum.Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    NS = "NS"


class SslStatus(str, enum.Enum):
    NOT_ISSUED = "not_issued"
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    EXPIRED = "expired"


class WordPressStatus(str, enum.Enum):
    PENDING = "pending"
    INSTALLED = "installed"
    FAILED = "failed"


class BackupStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"
    RESTORED = "restored"


class HostingToolActionLog(Base):
    __tablename__ = "hosting_tool_action_logs"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    tool = Column(String, nullable=False)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=True)
    raw_response = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DnsRecord(Base):
    __tablename__ = "dns_records"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    record_type = Column(Enum(DnsRecordType), nullable=False)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SslCertificate(Base):
    __tablename__ = "ssl_certificates"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    status = Column(Enum(SslStatus), default=SslStatus.NOT_ISSUED)
    issuer = Column(String, nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    email_address = Column(String, nullable=False, index=True)
    quota_mb = Column(Integer, default=1024)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HostingDatabase(Base):
    __tablename__ = "hosting_databases"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    database_name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WordPressInstall(Base):
    __tablename__ = "wordpress_installs"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    site_url = Column(String, nullable=False)
    admin_username = Column(String, nullable=False)
    status = Column(Enum(WordPressStatus), default=WordPressStatus.PENDING)
    install_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    installed_at = Column(DateTime(timezone=True), nullable=True)


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    backup_type = Column(String, default="full")
    status = Column(Enum(BackupStatus), default=BackupStatus.QUEUED)
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class HostingUsageSnapshot(Base):
    __tablename__ = "hosting_usage_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    disk_used_mb = Column(Integer, default=0)
    bandwidth_used_mb = Column(Integer, default=0)
    inode_used = Column(Integer, default=0)
    email_accounts = Column(Integer, default=0)
    databases = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FileManagerEntry(Base):
    __tablename__ = "file_manager_entries"

    id = Column(Integer, primary_key=True, index=True)
    hosting_order_id = Column(Integer, ForeignKey("hosting_orders.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("file_manager_entries.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    entry_type = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
