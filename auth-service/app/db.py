import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Base, User
from .config import DATABASE_URL



logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL)


Session = sessionmaker(
  engine,
  class_=AsyncSession,
  expire_on_commit=False
)

async def db_init():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de datos inicializada.")