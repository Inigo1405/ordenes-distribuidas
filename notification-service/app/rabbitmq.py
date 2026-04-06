import json
import logging
import pika

# from .schemas import InternalNotification
from .redis_client import redis_client
from .db import SessionLocal
from .repositories.notification_repo import insert_notification

logger = logging.getLogger(__name__)

def process_message(channel, method, properties, body):
  event = json.loads(body)

  try:
    logger.info(f"[notification-service] Mensaje recibido: {event['order_id']}")
    channel.basic_ack(delivery_tag=method.delivery_tag)
  except Exception as e:
    logger.error(f"Error procesando mensaje: {e}")
    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)



async def start_consumer(rabbit_url: str):
  connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
  channel = connection.channel()
  channel.exchange_declare(exchange="orders", exchange_type="topic", durable=True)
  channel.queue_declare(queue="notification.queue", durable=True)
  channel.queue_bind(
    queue="notification.queue",
    exchange="orders",
    routing_key="order.*"
  )
  channel.basic_qos(prefetch_count=1) 
  channel.basic_consume(
    queue="notification.queue", 
    on_message_callback=process_message
  )
  logger.info("Notification-service escuchando notification.queue...")
  channel.start_consuming()