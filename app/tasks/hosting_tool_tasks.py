# app/tasks/hosting_tool_tasks.py
from datetime import datetime
from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.models.hosting import HostingOrder, HostingStatus
from app.models.hosting_tools import (
    BackupJob,
    BackupStatus,
    HostingUsageSnapshot,
    WordPressInstall,
    WordPressStatus,
)
from app.services.hosting_tools import log_tool_action


@celery_app.task(name="tasks.install_wordpress_mock")
def install_wordpress_mock(install_id: int):
    db = SessionLocal()
    try:
        install = db.query(WordPressInstall).filter(WordPressInstall.id == install_id).first()
        if not install:
            return "WordPress install not found."

        install.status = WordPressStatus.INSTALLED
        install.installed_at = datetime.utcnow()
        install.install_error = None
        log_tool_action(
            db,
            install.hosting_order_id,
            "wordpress",
            "install",
            "success",
            "Simulated WordPress installation completed.",
        )
        db.commit()
        return f"WordPress install #{install_id} completed."
    finally:
        db.close()


@celery_app.task(name="tasks.run_backup_mock")
def run_backup_mock(backup_id: int):
    db = SessionLocal()
    try:
        backup = db.query(BackupJob).filter(BackupJob.id == backup_id).first()
        if not backup:
            return "Backup job not found."

        backup.status = BackupStatus.COMPLETED
        backup.message = "Simulated backup completed."
        backup.completed_at = datetime.utcnow()
        log_tool_action(
            db,
            backup.hosting_order_id,
            "backup",
            "create",
            "success",
            "Simulated backup completed.",
        )
        db.commit()
        return f"Backup job #{backup_id} completed."
    finally:
        db.close()


@celery_app.task(name="tasks.restore_backup_mock")
def restore_backup_mock(backup_id: int):
    db = SessionLocal()
    try:
        backup = db.query(BackupJob).filter(BackupJob.id == backup_id).first()
        if not backup:
            return "Backup job not found."

        backup.status = BackupStatus.RESTORED
        backup.message = "Simulated backup restore completed."
        backup.completed_at = datetime.utcnow()
        log_tool_action(
            db,
            backup.hosting_order_id,
            "backup",
            "restore",
            "success",
            "Simulated backup restore completed.",
        )
        db.commit()
        return f"Backup job #{backup_id} restored."
    finally:
        db.close()


@celery_app.task(name="tasks.sync_usage_mock")
def sync_usage_mock(hosting_order_id: int):
    db = SessionLocal()
    try:
        snapshot = HostingUsageSnapshot(
            hosting_order_id=hosting_order_id,
            disk_used_mb=512,
            bandwidth_used_mb=2048,
            inode_used=1200,
            email_accounts=2,
            databases=1,
        )
        db.add(snapshot)
        log_tool_action(
            db,
            hosting_order_id,
            "usage",
            "sync",
            "success",
            "Simulated resource usage sync completed.",
        )
        db.commit()
        return f"Usage sync completed for hosting order #{hosting_order_id}."
    finally:
        db.close()


@celery_app.task(name="tasks.sync_all_usage_mock")
def sync_all_usage_mock():
    db = SessionLocal()
    try:
        orders = (
            db.query(HostingOrder)
            .filter(HostingOrder.status.in_([HostingStatus.ACTIVE, HostingStatus.SUSPENDED]))
            .all()
        )
        synced = 0
        for order in orders:
            snapshot = HostingUsageSnapshot(
                hosting_order_id=order.id,
                disk_used_mb=512,
                bandwidth_used_mb=2048,
                inode_used=1200,
                email_accounts=2,
                databases=1,
            )
            db.add(snapshot)
            log_tool_action(
                db,
                order.id,
                "usage",
                "scheduled_sync",
                "success",
                "Scheduled simulated resource usage sync completed.",
            )
            synced += 1
        db.commit()
        return {"synced_hosting_orders": synced}
    finally:
        db.close()
