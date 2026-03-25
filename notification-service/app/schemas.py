from pydantic import BaseModel

class InternalNotification(BaseModel):
    order_id: str
    customer: str
    event_type: str
    message: str
    reason: str | None = None
    created_at: str