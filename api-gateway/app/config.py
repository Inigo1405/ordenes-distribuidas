import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

WRITER_URL = os.getenv("WRITER_SERVICE_URL")
AUTH_URL = os.getenv("AUTH_SERVICE_URL")
