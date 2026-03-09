from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):

    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    customer = Column(String)
    items = Column(JSON)