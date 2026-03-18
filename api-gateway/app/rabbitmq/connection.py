import pika
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS")


def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )
    
    return pika.BlockingConnection(params)


def get_channel():
    conn = get_connection()
    channel = conn.channel()
    
    return channel, conn
