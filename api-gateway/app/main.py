from fastapi import FastAPI, Header
import uuid

from .schemas import OrderCreate
from .redis_client import redis_client
from .services.writer_client import send_order

app = FastAPI()

@app.post("/orders")
async def create_order(order: OrderCreate, x_request_id: str | None = Header(default=None)):

    request_id = x_request_id or str(uuid.uuid4())

    order_id = str(uuid.uuid4())

    redis_client.set(order_id, "RECEIVED")

    payload = {
        "order_id": order_id,
        "customer": order.customer,
        "items": [i.dict() for i in order.items]
    }

    try:
        await send_order(payload, request_id)
    except Exception:
        redis_client.set(order_id, "FAILED")

    return {
        "order_id": order_id,
        "status": redis_client.get(order_id)
    }


@app.get("/orders/{order_id}")
async def get_order(order_id: str):

    status = redis_client.get(order_id)

    return {
        "order_id": order_id,
        "status": status
    }