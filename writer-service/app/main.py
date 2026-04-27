import asyncio
import logging

from .db import engine
from .models import Base
from .rabbitmq import start_consumer
from .config import RABBIT_URL

logging.basicConfig(level=logging.INFO)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await start_consumer(RABBIT_URL)


if __name__ == "__main__":
    asyncio.run(main())
