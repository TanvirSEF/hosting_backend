from sqlalchemy.orm import Session
from app.models.security import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    actor_user_id: int = None,
    resource_type: str = None,
    resource_id: str = None,
    message: str = None,
    ip_address: str = None,
    user_agent: str = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    return log
