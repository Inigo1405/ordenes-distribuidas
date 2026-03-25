from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Product(Base):
    """Producto con su stock disponible."""
    __tablename__ = "products"

    sku = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
