import pika
from ..config import RABBITMQ_HOST, RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS


def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30
    )
    return pika.BlockingConnection(params)


def get_channel():
    conn = get_connection()
    channel = conn.channel()
    return channel, conn
