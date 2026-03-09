from fastapi import FastAPI, Header

from .schemas import InternalOrder
from .redis_client import redis_client
from .db import SessionLocal, engine
from .models import Base
from .repositories.orders_repo import insert_order

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.post("/internal/orders")
async def persist_order(order: InternalOrder, x_request_id: str | None = Header(default=None)):
    async with SessionLocal() as session:
        try:
            await insert_order(session, order)
            redis_client.set(order.order_id, "PERSISTED")
            return {"status": "ok"}

        except Exception as e:
            redis_client.set(order.order_id, "FAILED")
            return {
                "status": "error",
                "message": str(e)    
            }