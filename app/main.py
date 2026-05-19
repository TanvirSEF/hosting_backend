# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.hosting import router as hosting_router
from app.api.v1.billing import router as billing_router
from app.api.v1.domain import router as domain_router
from app.api.v1.admin import router as admin_router
from app.api.v1.health import router as diagnostics_router
from app.api.v1.support import router as support_router
from app.api.v1.dns import router as dns_router
from app.api.v1.ssl import router as ssl_router
from app.api.v1.email import router as email_router
from app.api.v1.databases import router as databases_router
from app.api.v1.wordpress import router as wordpress_router
from app.api.v1.backups import router as backups_router
from app.api.v1.usage import router as usage_router
from app.api.v1.files import router as files_router
from app.api.v1.whmcs import router as whmcs_router


app = FastAPI(
    title="NexHost Custom Automation API",
    description="Backend automation engine for NexHost replacing WHMCS",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(hosting_router, prefix="/api/v1/hosting", tags=["Hosting"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(domain_router, prefix="/api/v1/domain", tags=["Domain Management"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(diagnostics_router, prefix="/api/v1/health", tags=["Health Diagnostics"])
app.include_router(support_router, prefix="/api/v1/support", tags=["Support"])
app.include_router(dns_router, prefix="/api/v1/dns", tags=["DNS Manager"])
app.include_router(ssl_router, prefix="/api/v1/ssl", tags=["SSL Manager"])
app.include_router(email_router, prefix="/api/v1/email", tags=["Email Manager"])
app.include_router(databases_router, prefix="/api/v1/databases", tags=["Database Manager"])
app.include_router(wordpress_router, prefix="/api/v1/wordpress", tags=["WordPress Installer"])
app.include_router(backups_router, prefix="/api/v1/backups", tags=["Backups"])
app.include_router(usage_router, prefix="/api/v1/usage", tags=["Usage Analytics"])
app.include_router(files_router, prefix="/api/v1/files", tags=["File Manager"])
app.include_router(whmcs_router, prefix="/api/v1/admin/whmcs", tags=["WHMCS Migration"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to NexHost Automation Engine Backend!"
    }
