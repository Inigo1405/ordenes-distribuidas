from fastapi import FastAPI, Header
from datetime import datetime, timezone
import json
import uuid

from .schemas import OrderCreate
from .redis_client import redis_client
from .services.writer_client import send_order

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "La API gateway está en funcionamiento. =D"}


@app.post("/orders")
async def create_order(order: OrderCreate, x_request_id: str | None = Header(default=None)):
    request_id = x_request_id or str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    redis_client.set(order_id, "RECEIVED")
    created_at = datetime.now(timezone.utc).isoformat()

    redis_client.hset(f"order:{order_id}", mapping={
        "customer": order.customer,
        "items": json.dumps([i.dict() for i in order.items]),
        "created_at": created_at
    })

    payload = {
        "order_id": order_id,
        "customer": order.customer,
        "items": [i.dict() for i in order.items],
        "created_at": created_at
    }

    try:
        await send_order(payload, request_id)
        return {
            "order_id": order_id,
            "status": redis_client.get(order_id)
        }
        
    except Exception as e:
        redis_client.set(order_id, "FAILED")
        return {
            "order_id": order_id,
            "status": redis_client.get(order_id),
            "error": str(e)
        }


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    status = redis_client.get(order_id)

    if status is None:
        redis_client.set(order_id, "FAILED")
        return {
            "error": "Orden no encontrada",
            "status": status
        }

    order_data = redis_client.hgetall(f"order:{order_id}")

    return {
        "order_id": order_id,
        "status": status,
        "data": order_data
    }