import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from .models import Base, Product
from .config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL)


SEED_PRODUCTS = [
  {"sku": "CTL-001", "name": "Control", "stock": 10},
  {"sku": "CTL-002", "name": "Controller", "stock": 40},
  {"sku": "CTL-003", "name": "Control Panel", "stock": 15},
  {"sku": "CTL-004", "name": "Control Box", "stock": 70},
]

Session = sessionmaker(
  engine,
  class_=AsyncSession,
  expire_on_commit=False
)

async def db_init():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    
  async with Session() as session:
    result = await session.execute(select(func.count(Product.sku)))
    count = result.scalar_one()
    if count == 0:
        session.add_all([Product(**prod) for prod in SEED_PRODUCTS])
        await session.commit()
        logger.info("Inventario inicializado con productos.")
    else:
      logger.info("Inventario con productos existentes.")