from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.hosting import HostingOrder
from app.models.hosting_tools import HostingToolActionLog


def get_owned_hosting_order(db: Session, hosting_order_id: int, user_id: int) -> HostingOrder:
    order = (
        db.query(HostingOrder)
        .filter(HostingOrder.id == hosting_order_id, HostingOrder.user_id == user_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Hosting order not found.")
    return order


def log_tool_action(
    db: Session,
    hosting_order_id: int,
    tool: str,
    action: str,
    status: str = "success",
    message: str = "Simulated provider action completed.",
    raw_response: str = None,
) -> HostingToolActionLog:
    log = HostingToolActionLog(
        hosting_order_id=hosting_order_id,
        tool=tool,
        action=action,
        status=status,
        message=message,
        raw_response=raw_response,
    )
    db.add(log)
    return log
