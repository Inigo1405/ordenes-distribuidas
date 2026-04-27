from pydantic import BaseModel
from typing import List


class Item(BaseModel):
    sku: str
    qty: int


class InternalOrder(BaseModel):
    order_id: str
    customer: str
    items: List[Item]
    created_at: str
