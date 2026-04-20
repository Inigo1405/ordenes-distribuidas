from fastapi import FastAPI, Header, HTTPException
from datetime import datetime, timezone
import json
import pika
import uuid
import httpx

from .schemas import OrderCreate
from .redis_client import redis_client
from .services.auth_client import send_auth
from .services.rabbit import get_channel
from .config import AUTH_URL


app = FastAPI()

channel = get_channel()


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
        "request_id": request_id,
        "order_id": order_id,
        "customer": order.customer,
        "items": [i.dict() for i in order.items],
        "created_at": created_at
    }

    try:
        channel.basic_publish(
            exchange="orders",
            routing_key="order.created", # Topic key
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,     # Mensaje persistente
                content_type="application/json"
            )
        )
        
        return {"order_id": order_id, "status": redis_client.get(order_id)}
        
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


@app.get("/auth/health")
async def auth_health():
    send_auth()
    url = f"{AUTH_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(url)
        r.raise_for_status()
        return r.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")


@app.post("/login")
async def auth_login():
    return 