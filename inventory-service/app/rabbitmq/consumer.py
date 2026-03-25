import json
import asyncio
import logging
from datetime import datetime, timezone

from .connection import get_channel
from ..db import SessionLocal, engine
from ..models import Base
from ..redis_client import redis_client
from ..repositories.inventory_repo import deduct_stock, seed_products

logger = logging.getLogger(__name__)

# Constantes que definen la topología de RabbitMQ para este servicio
EXCHANGE_NAME = "orders"
QUEUE_NAME = "inventory"
ROUTING_KEY = "order.created"


def _setup_exchange_and_queue(channel):
    """Declara el exchange, la cola y el binding."""
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="direct",
        durable=True
    )
    # Declara la cola durable para que los mensajes no se pierdan si el servicio cae
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    # Enlaza la cola al exchange: solo llegarán mensajes con routing key "order.created"
    channel.queue_bind(
        queue=QUEUE_NAME,
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY
    )


async def _process_order(order: dict):
    """
    Descuenta el stock de cada ítem de la orden.
    Actualiza el estado en Redis a STOCK_DEDUCTED o INSUFFICIENT_STOCK.
    """
    order_id = order["order_id"]
    items = order.get("items", [])
    results = []
    all_ok = True

    # Abre una sesión de DB y recorre cada ítem de la orden
    async with SessionLocal() as session:
        for item in items:
            sku = item["sku"]
            qty = item["qty"]

            # Intenta descontar el stock del producto; retorna dict con {"ok": bool, ...}
            result = await deduct_stock(session, sku, qty)
            results.append(result)
            if not result["ok"]:
                all_ok = False
                logger.warning(
                    "Stock insuficiente order=%s sku=%s motivo=%s",
                    order_id, sku, result.get("reason")
                )

    # Determina el estado final según si todos los ítems tuvieron stock suficiente
    new_status = "STOCK_DEDUCTED" if all_ok else "INSUFFICIENT_STOCK"
    # Guarda el estado simple en Redis (clave plana) para consultas rápidas
    redis_client.set(order_id, new_status)
    # Guarda el detalle completo en un hash de Redis para trazabilidad
    redis_client.hset(f"order:{order_id}", mapping={
        "inventory_status": new_status,
        "inventory_checked_at": datetime.now(timezone.utc).isoformat(),
        "inventory_detail": json.dumps(results)
    })

    logger.info("Orden %s procesada → %s", order_id, new_status)
    return all_ok, results


def _on_message(channel, method, properties, body):
    """Callback síncrono de pika → lanza la corrutina en asyncio."""
    try:
        # Deserializa el mensaje JSON recibido de RabbitMQ
        order = json.loads(body)
        logger.info("Orden recibida: %s", order.get("order_id"))
        # Como pika es síncrono, se usa asyncio.run() para ejecutar la corrutina
        # de procesamiento desde este contexto bloqueante
        asyncio.run(_process_order(order))
        # Confirma a RabbitMQ que el mensaje fue procesado exitosamente
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        logger.exception("Error procesando mensaje: %s", exc)
        # Rechaza el mensaje sin reencolar (requeue=False) para evitar bucles infinitos
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


async def startup_db():
    """Crea tablas y siembra productos de ejemplo."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Inserta productos iniciales en la base de datos
    async with SessionLocal() as session:
        await seed_products(session)


def start_consumer():
    """Inicia el consumer bloqueante (se llama desde main.py en un thread)."""
    asyncio.run(startup_db())

    channel, conn = get_channel()
    _setup_exchange_and_queue(channel)
    channel.basic_qos(prefetch_count=1)
    # Registra _on_message como el callback que se ejecuta por cada mensaje entrante
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=_on_message
    )
    logger.info("Inventory consumer arriba. Esperando mensajes en '%s'...", QUEUE_NAME)
    channel.start_consuming()
