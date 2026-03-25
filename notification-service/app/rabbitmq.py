import asyncio
import json
import logging

import pika
from .schemas import InternalNotification
from .redis_client import redis_client
from .repositories.notification_repo import insert_notification
from .db import SessionLocal

logger = logging.getLogger(__name__)

# async def process_message(message: aio_pika.IncomingMessage):
#   async with message.process(requeue=False):
#     payload = json.loads(message.body)

#     request_id = payload["request_id"]
#     order_id   = payload["order_id"]

#     logger.info(f"[{request_id}] Procesando orden {order_id}")

#     order = InternalOrder(**payload)

#     async with SessionLocal() as session:
#       try:
#         await insert_notification(session, order)
#         redis_client.set(order_id, "PERSISTED")
#         logger.info(f"[{request_id}] Orden {order_id} persistida ✓")

#       except Exception as e:
#         redis_client.set(order_id, "FAILED")
#         logger.error(f"[{request_id}] Error persistiendo {order_id}: {e}")
#         raise



async def start_consumer(rabbit_url: str):
  pass