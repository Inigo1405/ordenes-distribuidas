from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()
class Order(Base):
    """Modelo ORM (Order)"""

    __tablename__ = "orders"

    order_id = Column(String(36), primary_key=True)
    customer = Column(String(255))
    items = Column(JSON)
    created_at = Column(DateTime)

    """
    {
        "customer": "Pingul",
        "items": [
            {
            "sku": "01-002-0014",
            "qty": 5
            }
        ]
    }
    """