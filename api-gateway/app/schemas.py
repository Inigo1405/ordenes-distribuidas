from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    sku: str
    qty: int

class OrderCreate(BaseModel):
    customer: str
    items: List[Item]