from sqlalchemy import select
from ..models import Order


async def insert_order(session, order):
    result = await session.execute(
        select(Order).where(Order.order_id == order.order_id)
    )
    existing = result.scalar()

    if existing:
        return existing

    new_order = Order(
        order_id=order.order_id,
        customer=order.customer,
        items=[i.dict() for i in order.items],
    )

    session.add(new_order)
    await session.commit()

    return new_order
