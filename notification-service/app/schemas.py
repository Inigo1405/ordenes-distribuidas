from pydantic import BaseModel
from datetime import datetime

class InternalNotification(BaseModel):
    order_id: str
    customer: str
    event_type: str
    message: str
    reason: str | None = None
    created_at: datetime