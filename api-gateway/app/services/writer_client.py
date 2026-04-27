import httpx
from ..config import WRITER_URL


async def send_order(order, request_id):
    for attempt in range(2):  # retry 1 vez
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                r = await client.post(
                    WRITER_URL, json=order, headers={"X-Request-Id": request_id}
                )
                return r.json()

        except httpx.RequestError:
            if attempt == 1:
                raise
