# app/tasks/hosting_tasks.py
from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.models.hosting import HostingOrder, HostingStatus
from app.services.whm import whm_service
import asyncio

@celery_app.task(name="tasks.provision_cpanel_async", bind=True, max_retries=3)
def provision_cpanel_async(self, order_id: int, contact_email: str):
    """
    Background worker task execution block that calls WHM API out-of-band.
    If the remote server drops connectivity, Celery automatically retries.
    """
    db = SessionLocal()
    try:
        # Fetch the target hosting order from the database
        order = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
        if not order:
            return "Order not found inside database row execution context."

        # Running async service module adapter inside Celery sync wrapper loop safely
        loop = asyncio.get_event_loop()
        whm_result = loop.run_until_complete(
            whm_service.create_cpanel_account(
                domain=order.domain,
                plan_package=order.package_name,
                contact_email=contact_email
            )
        )

        if whm_result.get("success"):
            # Provisioning succeeded, update database metrics instantly
            order.username = whm_result.get("username")
            order.status = HostingStatus.ACTIVE
            db.commit()
            return f"Successfully provisioned account for order #{order_id}"
        else:
            # WHM failed, trigger automated worker level retry protocol
            raise Exception(whm_result.get("error", "Unknown automation engine failure."))

    except Exception as exc:
        db.close()
        # Retries background operation safely after a 60-second backoff delay window
        raise self.retry(exc=exc, countdown=60)
        
    finally:
        db.close()