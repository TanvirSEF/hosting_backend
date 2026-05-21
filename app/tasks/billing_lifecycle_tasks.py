from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.services.billing_lifecycle import (
    generate_renewal_invoices,
    mark_due_reminders,
    process_overdue_services,
)


@celery_app.task(name="tasks.generate_renewal_invoices")
def generate_renewal_invoices_task(days_ahead: int = 7):
    db = SessionLocal()
    try:
        result = generate_renewal_invoices(db, days_ahead=days_ahead)
        db.commit()
        return result
    finally:
        db.close()


@celery_app.task(name="tasks.mark_due_reminders")
def mark_due_reminders_task(days_ahead: int = 3):
    db = SessionLocal()
    try:
        count = mark_due_reminders(db, days_ahead=days_ahead)
        db.commit()
        return {"reminders_marked": count}
    finally:
        db.close()


@celery_app.task(name="tasks.process_overdue_services")
def process_overdue_services_task():
    db = SessionLocal()
    try:
        result = process_overdue_services(db)
        db.commit()
        return result
    finally:
        db.close()
