import threading
import logging

from fastapi import FastAPI
from sqlalchemy import select

from .db import SessionLocal
from .models import Product
from .rabbitmq.consumer import start_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Inventory Service")


@app.on_event("startup")
async def startup():
    """Lanza el consumer de RabbitMQ en un hilo separado."""
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    logger.info("Consumer de inventario iniciado en background thread")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory-service"}


@app.get("/inventory")
async def list_inventory():
    """Lista el stock actual de todos los productos."""
    async with SessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        return [
            {"sku": p.sku, "name": p.name, "stock": p.stock}
            for p in products
        ]


@app.get("/inventory/{sku}")
async def get_stock(sku: str):
    """Consulta el stock de un SKU específico."""
    async with SessionLocal() as session:
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalar()
        if product is None:
            return {"error": f"SKU '{sku}' no encontrado"}, 404
        return {"sku": product.sku, "name": product.name, "stock": product.stock}
