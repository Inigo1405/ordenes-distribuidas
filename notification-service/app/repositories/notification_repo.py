from sqlalchemy import select
from ..models import Notification


async def insert_notification(session, notification):
    result = await session.execute(
        select(Notification).where(Notification.order_id == notification.order_id)
    )
    existing = result.scalar()

    if existing:
        return existing

    new_notification = Notification(
        order_id=notification.order_id,
        customer=notification.customer,
        event_type=notification.event_type,
        message=notification.message,
        reason=notification.reason,
        created_at=notification.created_at,
    )

    session.add(new_notification)
    await session.commit()

    return new_notification
