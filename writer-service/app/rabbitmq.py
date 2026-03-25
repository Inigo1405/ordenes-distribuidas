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
  async with message.process(requeue=False):
    payload = json.loads(message.body)

    request_id = payload["request_id"]
    order_id   = payload["order_id"]

    logger.info(f"[{request_id}] Procesando orden {order_id}")

    order = InternalOrder(**payload)

    async with SessionLocal() as session:
      try:
        await insert_order(session, order)
        redis_client.set(order_id, "PERSISTED")
        logger.info(f"[{request_id}] Orden {order_id} persistida ✓")

      except Exception as e:
        redis_client.set(order_id, "FAILED")
        logger.error(f"[{request_id}] Error persistiendo {order_id}: {e}")
        raise



async def start_consumer(rabbit_url: str):
  conn = await aio_pika.connect_robust(
    rabbit_url,
    fail_fast=False,
    heartbeat=30
  )

  async with conn:
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
      "orders",
      aio_pika.ExchangeType.TOPIC,
      durable=True
    )

    queue = await channel.declare_queue("writer.queue", durable=True)
    await queue.bind(exchange, routing_key="order.created")

    await queue.consume(process_message)

    logger.info("Writer-service escuchando writer.queue...")
    await asyncio.Future()