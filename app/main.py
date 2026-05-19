# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.session import Base, engine
from app.models import user, hosting, billing 
from app.api.v1.auth import router as auth_router
from app.api.v1.hosting import router as hosting_router
from app.api.v1.billing import router as billing_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexHost Custom Automation API",
    description="Backend automation engine for NexHost replacing WHMCS",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(hosting_router, prefix="/api/v1/hosting", tags=["Hosting"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
