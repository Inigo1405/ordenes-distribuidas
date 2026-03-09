from fastapi import FastAPI, Header
import redis

from .schemas import InternalOrder
from .config import REDIS_HOST, REDIS_PORT
from .db import SessionLocal
from .repositories.orders_repo import insert_order

app = FastAPI()

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

@app.post("/internal/orders")
async def persist_order(order: InternalOrder, x_request_id: str | None = Header(default=None)):

    async with SessionLocal() as session:

        try:
            await insert_order(session, order)

            redis_client.set(order.order_id, "PERSISTED")

            return {"status": "ok"}

        except Exception:

            redis_client.set(order.order_id, "FAILED")

            return {"status": "error"}