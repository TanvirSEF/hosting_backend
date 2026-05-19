from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.hosting_tools import BackupStatus, DnsRecordType, SslStatus, WordPressStatus


class HostingToolActionLogOut(BaseModel):
    id: int
    hosting_order_id: int
    tool: str
    action: str
    status: str
    message: Optional[str]
    raw_response: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DnsRecordCreate(BaseModel):
    record_type: DnsRecordType
    name: str
    value: str
    ttl: int = 3600
    priority: Optional[int] = None


class DnsRecordUpdate(BaseModel):
    name: str
    value: str
    ttl: int = 3600
    priority: Optional[int] = None


class DnsRecordOut(BaseModel):
    id: int
    hosting_order_id: int
    record_type: DnsRecordType
    name: str
    value: str
    ttl: int
    priority: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class SslCertificateOut(BaseModel):
    id: int
    hosting_order_id: int
    domain: str
    status: SslStatus
    issuer: Optional[str]
    issued_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class EmailAccountCreate(BaseModel):
    local_part: str
    password: str
    quota_mb: int = 1024


class EmailPasswordUpdate(BaseModel):
    password: str


class EmailAccountOut(BaseModel):
    id: int
    hosting_order_id: int
    email_address: str
    quota_mb: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HostingDatabaseCreate(BaseModel):
    database_name: str
    username: str
    password: str


class HostingDatabaseOut(BaseModel):
    id: int
    hosting_order_id: int
    database_name: str
    username: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WordPressInstallCreate(BaseModel):
    site_url: str
    admin_username: str
    admin_password: str


class WordPressInstallOut(BaseModel):
    id: int
    hosting_order_id: int
    site_url: str
    admin_username: str
    status: WordPressStatus
    install_error: Optional[str]
    created_at: datetime
    installed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BackupCreate(BaseModel):
    backup_type: str = "full"


class BackupJobOut(BaseModel):
    id: int
    hosting_order_id: int
    backup_type: str
    status: BackupStatus
    message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class UsageSnapshotOut(BaseModel):
    id: int
    hosting_order_id: int
    disk_used_mb: int
    bandwidth_used_mb: int
    inode_used: int
    email_accounts: int
    databases: int
    created_at: datetime

    class Config:
        from_attributes = True


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FileMetadataCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    size_bytes: int = 0


class FileManagerEntryOut(BaseModel):
    id: int
    hosting_order_id: int
    parent_id: Optional[int]
    name: str
    path: str
    entry_type: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True
