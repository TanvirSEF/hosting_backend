# app/core/celery_app.py
from celery import Celery
import os

# Read Redis URL from environment variables or use local default loopback
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# Initialize Celery application engine instance
celery_app = Celery(
    "nexhost_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.hosting_tasks"],
)

# Optional configuration updates for processing reliability
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)

# Import task modules so workers launched with this Celery app register them.
import app.tasks.hosting_tasks  # noqa: E402,F401
