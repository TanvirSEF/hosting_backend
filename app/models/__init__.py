# app/models/__init__.py updates
from app.database.session import Base
from app.models.user import User
from app.models.hosting import HostingOrder, HostingPackage
from app.models.billing import Invoice, PaymentLog
from app.models.domain import UserDomain # Added domain model reference
from app.models.automation import AutomationLog
from app.models.support import SupportTicket, SupportTicketMessage
from app.models.hosting_tools import (
    BackupJob,
    DnsRecord,
    EmailAccount,
    FileManagerEntry,
    HostingDatabase,
    HostingToolActionLog,
    HostingUsageSnapshot,
    SslCertificate,
    WordPressInstall,
)
from app.models.whmcs import WhmcsImportBatch, WhmcsImportRow

__all__ = [
    "Base",
    "User",
    "HostingOrder",
    "HostingPackage",
    "Invoice",
    "PaymentLog",
    "UserDomain",
    "AutomationLog",
    "SupportTicket",
    "SupportTicketMessage",
    "HostingToolActionLog",
    "DnsRecord",
    "SslCertificate",
    "EmailAccount",
    "HostingDatabase",
    "WordPressInstall",
    "BackupJob",
    "HostingUsageSnapshot",
    "FileManagerEntry",
    "WhmcsImportBatch",
    "WhmcsImportRow",
]
