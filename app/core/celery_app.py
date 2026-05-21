# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

# Initialize Celery application engine instance
celery_app = Celery(
    "nexhost_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.hosting_tasks", "app.tasks.hosting_tool_tasks", "app.tasks.billing_lifecycle_tasks"],
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
import app.tasks.hosting_tool_tasks  # noqa: E402,F401
import app.tasks.billing_lifecycle_tasks  # noqa: E402,F401
