# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.session import Base, engine
from app.models import user, hosting, billing 


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexHost Custom Automation API",
    description="Backend automation engine for NexHost replacing WHMCS",
    version="1.0.0"
)

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