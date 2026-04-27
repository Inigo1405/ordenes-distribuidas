import asyncio
import json
import logging

import aio_pika
from .schemas import InternalOrder
from .redis_client import redis_client
from .repositories.orders_repo import insert_order
from .db import SessionLocal

logger = logging.getLogger(__name__)


async def process_message(message: aio_pika.IncomingMessage):
    # Procesa el mensaje dentro de un context manager que lo acknowledges al terminar.
    # Si ocurre una excepción, requeue=False evita que el mensaje regrese a la cola.
    async with message.process(requeue=False):
        # Deserializa el cuerpo del mensaje de bytes JSON a diccionario Python
        payload = json.loads(message.body)

        # Extrae los identificadores principales para logging y seguimiento
        request_id = payload["request_id"]
        order_id = payload["order_id"]

        logger.info(f"[{request_id}] Procesando orden {order_id}")

        # Valida y construye el objeto de orden con el schema definido
        order = InternalOrder(**payload)

        async with SessionLocal() as session:
            try:
                # Persiste la orden en la base de datos
                await insert_order(session, order)

                # Marca la orden como exitosa en Redis para que otros servicios puedan consultarlo
                redis_client.set(order_id, "PERSISTED")
                logger.info(f"[{request_id}] Orden {order_id} persistida ✓")

            except Exception as e:
                # Si falla la inserción, marca la orden como fallida en Redis
                redis_client.set(order_id, "FAILED")
                logger.error(f"[{request_id}] Error persistiendo {order_id}: {e}")
                raise


async def start_consumer(rabbit_url: str):
    # Crea una conexión robusta a RabbitMQ que se reconecta automáticamente si cae.
    # fail_fast=False evita que falle si RabbitMQ no está disponible al arrancar.
    # heartbeat=30 envía un ping cada 30 segundos para mantener la conexión viva.
    conn = await aio_pika.connect_robust(rabbit_url, fail_fast=False, heartbeat=30)

    async with conn:
        channel = await conn.channel()

        # Limita a procesar un mensaje a la vez para evitar sobrecarga del servicio
        await channel.set_qos(prefetch_count=1)

        # Declara el exchange de tipo TOPIC llamado "orders".
        # TOPIC permite enrutar mensajes por patrones en la routing key.
        # durable=True lo hace persistente ante reinicios de RabbitMQ.
        exchange = await channel.declare_exchange(
            "orders", aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Declara la cola durable donde llegarán los mensajes de este servicio
        queue = await channel.declare_queue("writer.queue", durable=True)

        # Enlaza la cola al exchange para recibir solo mensajes con routing key "order.created"
        await queue.bind(exchange, routing_key="order.created")

        # Registra process_message como el handler que se ejecutará por cada mensaje entrante
        await queue.consume(process_message)

        logger.info("Writer-service escuchando writer.queue...")
        await asyncio.Future()
