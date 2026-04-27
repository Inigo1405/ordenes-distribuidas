import os
from pathlib import Path

DATABASE_URL = os.getenv("USER_DATABASE_URL")

REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))


# Leer claves desde archivos .pem
BASE_DIR = Path(__file__).parent
with open(BASE_DIR / "private_key.pem", "r") as f:
    PRIVATE_KEY = f.read()

with open(BASE_DIR / "public_key.pem", "r") as f:
    PUBLIC_KEY = f.read()

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
