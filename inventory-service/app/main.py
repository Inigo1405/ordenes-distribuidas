import asyncio
import logging
import json
import pika

from .db import Session, db_init
from .models import Product
from .config import RABBIT_URL


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    asyncio.run(db_init())
    logger.info("Sistema de Inventario operando!")

    params = pika.URLParameters(RABBIT_URL)
    params.heartbeat = 120
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange="orders", exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="inventory.queue", exclusive=True)

    channel.queue_bind(
        exchange="orders", queue=result.method.queue, routing_key="order.created"
    )
    channel.basic_consume(
        queue=result.method.queue, on_message_callback=callback, auto_ack=True
    )

    logger.info("Inventario esperando...")
    channel.start_consuming()


def callback(ch, method, properties, body):
    order = json.loads(body)
    order_id = order.get("order_id")
    items = order.get("items", [])
    routing_key = "order.stock_"

    try:
        success, reason = update_inventory(order_id, items)
        if not success:
            logger.warning(f"Orden {order_id} - {reason}")
            event = {**order, "event": "STOCK_CREDITS_REJECTED", "reason": reason}
            routing_key += "rejected"
        else:
            event = {**order, "event": "STOCK_CONFIRMED"}
            logger.info(f"Orden {order_id} - {reason}")
            routing_key += "confirmed"

        ch.basic_publish(
            exchange="orders",
            routing_key=routing_key,
            body=json.dumps(event).encode(),
            properties=pika.BasicProperties(content_type="application/json"),
        )

    except Exception as e:
        logger.error(f"Error en la orden {order_id}: {e}")


def update_inventory(order_id, items):
    with Session() as session:
        for item in items:
            sku = item["sku"]
            qty = item.get("qty")
            product = (
                session.query(Product).filter_by(sku=sku).with_for_update().first()
            )

            if not product:
                session.rollback()
                reason = f"Producto no encontrado: {sku}"
                logger.warning(f"Orden {order_id} - {reason}")
                return False, reason

            elif product.stock < qty:
                session.rollback()
                reason = f"Stock insuficiente de: {sku}"
                logger.warning(f"Orden {order_id} - {reason}")
                return False, reason

            else:
                product.stock -= qty
                logger.info(f"Stock actualizado para: {sku}")

        session.commit()
        return True, "Inventario actualizado correctamente"


if __name__ == "__main__":
    main()
